import os
import json

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, send_file, abort, Response, stream_with_context
)
from werkzeug.utils import secure_filename
from markupsafe import Markup, escape

from config import Config
from database import db, init_db
from models import Contract, Clause, ChatMessage
from utils.pdf_parser import (
    DocumentExtractionError,
    clean_text,
    extraction_error_message,
    extract_text,
)
from utils.llm_analyzer import (
    LLMServiceError,
    analyze_contract,
    get_clause_comparison,
    safe_error_message,
    stream_chat_about_contract,
)
from utils.report_generator import generate_pdf_report, generate_docx_report

# ──────────────────────────────────────────────
# App Factory
# ──────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'static', 'reports'), exist_ok=True)

@app.template_filter('nl2br')
def nl2br_filter(value):
    if value is None:
        return ''
    return Markup(str(escape(value)).replace('\n', '<br/>'))

init_db(app)

ALLOWED_EXTENSIONS = {'pdf', 'txt'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _sse(payload: dict) -> str:
    """Encode one server-sent event for the browser chat client."""
    return f'data: {json.dumps(payload, ensure_ascii=False)}\n\n'


def _api_error(message: str, status: int):
    """Return consistent JSON errors for browser API callers."""
    return jsonify({'error': message}), status


# ──────────────────────────────────────────────
# Context Processors
# ──────────────────────────────────────────────
@app.context_processor
def inject_globals():
    return {
        'languages': Config.LANGUAGES,
        'contract_types': Config.CONTRACT_TYPES,
        # Keep error details useful while still filtering old/raw database
        # values before they reach the browser.
        'safe_error_message': safe_error_message,
    }


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.route('/')
def index():
    total_contracts  = Contract.query.count()
    recent_contracts = Contract.query.order_by(Contract.created_at.desc()).limit(5).all()
    total_clauses    = Clause.query.count()
    red_flags_found  = Clause.query.filter_by(is_red_flag=True).count()
    return render_template(
        'index.html',
        recent_contracts=recent_contracts,
        total_contracts=total_contracts,
        total_clauses=total_clauses,
        red_flags_found=red_flags_found,
    )


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'contract' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)

        file          = request.files['contract']
        language      = request.form.get('language', 'hindi')
        contract_type = request.form.get('contract_type', 'General Contract')

        if not file or file.filename == '':
            flash('Please select a file to upload.', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Only PDF and TXT files are supported.', 'danger')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            raw_text = extract_text(filepath)
            text     = clean_text(raw_text)
        except DocumentExtractionError as exc:
            app.logger.info('Document extraction failed: %s', exc)
            flash(str(exc), 'warning')
            return redirect(request.url)
        except Exception as exc:
            app.logger.exception('Contract file could not be read')
            flash(extraction_error_message(exc), 'danger')
            return redirect(request.url)

        if len(text.strip()) < 50:
            flash('File appears to be empty or unreadable.', 'warning')
            return redirect(request.url)

        contract = Contract(
            filename=filename,
            original_text=text,
            language=language,
            contract_type=contract_type,
            status='processing'
        )
        db.session.add(contract)
        db.session.commit()

        flash('File uploaded! Analyzing now...', 'success')
        return redirect(url_for('analyze', contract_id=contract.id))

    return render_template('upload.html')


@app.route('/analyze/<int:contract_id>')
def analyze(contract_id):
    contract = Contract.query.get_or_404(contract_id)

    if contract.status in ('processing', 'error'):
        Clause.query.filter_by(contract_id=contract_id).delete()
        db.session.commit()

        try:
            result = analyze_contract(contract.original_text, contract.language)

            contract.summary            = result.get('summary', '')
            contract.translated_summary = result.get('translated_summary', '')
            contract.risk_score         = result.get('overall_risk', 'Medium')
            contract.contract_type      = result.get('contract_type', contract.contract_type)
            contract.status             = 'completed'

            for cdata in result.get('clauses', []):
                clause = Clause(
                    contract_id    = contract.id,
                    clause_type    = cdata.get('type', 'General'),
                    original_text  = cdata.get('original', '')[:2000],
                    simplified_text= cdata.get('simplified', ''),
                    translated_text= cdata.get('translated', ''),
                    severity       = cdata.get('severity', 'Low'),
                    explanation    = cdata.get('explanation', ''),
                    is_red_flag    = cdata.get('is_red_flag', False),
                )
                db.session.add(clause)

            db.session.commit()
            flash('Analysis complete!', 'success')

        except LLMServiceError as exc:
            error_detail = safe_error_message(exc)
            contract.status = 'error'
            contract.summary = error_detail
            db.session.commit()
            flash('Analysis could not be completed. Please try again.', 'danger')
        except Exception:
            app.logger.exception('Contract analysis failed')
            error_detail = 'We could not analyze this contract right now. Please try again shortly.'
            contract.status       = 'error'
            contract.summary      = error_detail
            db.session.commit()
            flash('Analysis could not be completed. Please try again.', 'danger')

    clauses    = Clause.query.filter_by(contract_id=contract_id).all()
    sev_counts = contract.severity_counts()

    return render_template(
        'analysis.html',
        contract=contract,
        clauses=clauses,
        sev_counts=sev_counts,
        sev_counts_json=sev_counts,
    )


@app.route('/report/<int:contract_id>')
def report(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    if contract.status != 'completed':
        flash('Contract analysis not yet complete.', 'warning')
        return redirect(url_for('analyze', contract_id=contract_id))

    clauses    = Clause.query.filter_by(contract_id=contract_id).all()
    sev_counts = contract.severity_counts()

    return render_template(
        'report.html',
        contract=contract,
        clauses=clauses,
        sev_counts=sev_counts,
        sev_counts_json=sev_counts,
    )


@app.route('/download/<int:contract_id>/<fmt>')
def download_report(contract_id, fmt):
    contract = Contract.query.get_or_404(contract_id)
    if contract.status != 'completed':
        flash('Contract analysis is not complete yet.', 'warning')
        return redirect(url_for('analyze', contract_id=contract_id))

    clauses = Clause.query.filter_by(contract_id=contract_id).all()

    try:
        if fmt == 'pdf':
            filepath = generate_pdf_report(contract, clauses)
            dl_name  = f'LegalEase_Report_{contract_id}.pdf'
            mime     = 'application/pdf'
        elif fmt == 'docx':
            filepath = generate_docx_report(contract, clauses)
            dl_name  = f'LegalEase_Report_{contract_id}.docx'
            mime     = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            abort(400)

        if not os.path.exists(filepath):
            flash('The report file could not be found. Please try again.', 'danger')
            return redirect(url_for('report', contract_id=contract_id))

        return send_file(filepath, as_attachment=True, download_name=dl_name, mimetype=mime)

    except Exception:
        app.logger.exception('Report download failed')
        flash('The report could not be generated. Please try again shortly.', 'danger')
        return redirect(url_for('report', contract_id=contract_id))


@app.route('/chatbot/<int:contract_id>', methods=['GET'])
def chatbot(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    messages = (
        ChatMessage.query
        .filter_by(contract_id=contract_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return render_template('chatbot.html', contract=contract, messages=messages)


@app.route('/api/chat/<int:contract_id>', methods=['POST'])
def chat_api(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    data = request.get_json(silent=True) or {}
    message_value = data.get('message') if isinstance(data, dict) else None

    if not isinstance(message_value, str) or not message_value.strip():
        return _api_error('Message cannot be empty.', 400)

    if not contract.original_text.strip():
        return _api_error('This contract has no readable text to discuss.', 422)

    if contract.status != 'completed':
        return _api_error('Complete the contract analysis before starting a chat.', 409)

    user_message = message_value.strip()[:500]

    # Save user message
    user_msg = ChatMessage(contract_id=contract_id, role='user', content=user_message)
    db.session.add(user_msg)
    db.session.commit()

    # Do not include the new user message in history; the analyzer adds it once.
    prev_msgs = (
        ChatMessage.query
        .filter_by(contract_id=contract_id)
        .filter(ChatMessage.id != user_msg.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(6)
        .all()
    )
    history = [{'role': m.role, 'content': m.content} for m in reversed(prev_msgs)]

    def generate():
        full_ai_text = []
        try:
            for chunk in stream_chat_about_contract(
                contract.original_text,
                user_message,
                contract.language,
                history,
            ):
                full_ai_text.append(chunk)
                yield _sse({'type': 'chunk', 'text': chunk})

            ai_msg = ChatMessage(
                contract_id=contract_id,
                role='assistant',
                content=''.join(full_ai_text),
            )
            db.session.add(ai_msg)
            db.session.commit()
            yield _sse({'type': 'done'})
        except LLMServiceError as exc:
            db.session.rollback()
            # A failed request should not leave an unanswered question in the
            # conversation history.
            stale_user_msg = db.session.get(ChatMessage, user_msg.id)
            if stale_user_msg is not None:
                db.session.delete(stale_user_msg)
                db.session.commit()
            yield _sse({'type': 'error', 'message': safe_error_message(exc)})
        except Exception:
            db.session.rollback()
            app.logger.exception('Chat response failed')
            stale_user_msg = db.session.get(ChatMessage, user_msg.id)
            if stale_user_msg is not None:
                db.session.delete(stale_user_msg)
                db.session.commit()
            yield _sse({
                'type': 'error',
                'message': 'We could not answer that right now. Please try again shortly.',
            })

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'X-Content-Type-Options': 'nosniff',
        },
    )


@app.route('/api/compare-clause', methods=['POST'])
def compare_clause_api():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _api_error('Invalid request body.', 400)
    clause_text = data.get('clause_text', '')
    clause_type = data.get('clause_type', 'General')

    if not isinstance(clause_text, str) or not clause_text.strip():
        return _api_error('No clause text provided.', 400)
    clause_text = clause_text.strip()[:2000]
    clause_type = str(clause_type or 'General').strip()[:100]

    try:
        comparison = get_clause_comparison(clause_text, clause_type)
        return jsonify({'comparison': comparison})
    except LLMServiceError as exc:
        return _api_error(safe_error_message(exc), 503)
    except Exception:
        app.logger.exception('Clause comparison failed')
        return _api_error('Comparison is temporarily unavailable. Please try again.', 500)


@app.route('/history')
def history():
    page      = request.args.get('page', 1, type=int)
    contracts = (
        Contract.query
        .order_by(Contract.created_at.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )
    return render_template('history.html', contracts=contracts)


@app.route('/delete/<int:contract_id>', methods=['POST'])
def delete_contract(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    db.session.delete(contract)
    db.session.commit()
    flash('Contract deleted successfully.', 'success')
    return redirect(url_for('history'))


# ──────────────────────────────────────────────
# Error Handlers
# ──────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return _api_error('The requested resource was not found.', 404)
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    if request.path.startswith('/api/'):
        return _api_error('Something went wrong. Please try again shortly.', 500)
    return render_template('errors/500.html'), 500


if __name__ == '__main__':
    api_key = os.getenv('SARVAM_API_KEY', '').strip()
    if not api_key:
        app.logger.warning('AI service is not configured; analysis and chat will be unavailable.')

    app.run(
        debug=app.config.get('DEBUG', False),
        host=os.getenv('HOST', '127.0.0.1'),
        port=int(os.getenv('PORT', '5001')),
    )
