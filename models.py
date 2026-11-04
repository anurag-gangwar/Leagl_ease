from database import db
from datetime import datetime


class Contract(db.Model):
    __tablename__ = 'contracts'

    id             = db.Column(db.Integer, primary_key=True)
    filename       = db.Column(db.String(255), nullable=False)
    original_text  = db.Column(db.Text, nullable=False)
    language       = db.Column(db.String(50), default='hindi')
    contract_type  = db.Column(db.String(100), default='General Contract')
    summary        = db.Column(db.Text, nullable=True)           # English plain summary
    translated_summary = db.Column(db.Text, nullable=True)       # Regional language summary
    risk_score     = db.Column(db.String(20), default='Unknown') # Low / Medium / High
    status         = db.Column(db.String(30), default='pending') # pending / processing / completed / error
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clauses        = db.relationship('Clause', backref='contract', lazy=True, cascade='all, delete-orphan')
    chat_messages  = db.relationship('ChatMessage', backref='contract', lazy=True, cascade='all, delete-orphan')

    def high_clauses(self):
        return [c for c in self.clauses if c.severity == 'High']

    def medium_clauses(self):
        return [c for c in self.clauses if c.severity == 'Medium']

    def low_clauses(self):
        return [c for c in self.clauses if c.severity == 'Low']

    def red_flag_clauses(self):
        return [c for c in self.clauses if c.is_red_flag]

    def severity_counts(self):
        return {
            'High':   len(self.high_clauses()),
            'Medium': len(self.medium_clauses()),
            'Low':    len(self.low_clauses()),
        }

    def risk_color(self):
        colors = {'High': 'danger', 'Medium': 'warning', 'Low': 'success', 'Unknown': 'secondary'}
        return colors.get(self.risk_score, 'secondary')

    def __repr__(self):
        return f'<Contract {self.id}: {self.filename}>'


class Clause(db.Model):
    __tablename__ = 'clauses'

    id               = db.Column(db.Integer, primary_key=True)
    contract_id      = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)
    clause_type      = db.Column(db.String(100), nullable=True)   # e.g. Auto-Renewal, Liability
    original_text    = db.Column(db.Text, nullable=False)
    simplified_text  = db.Column(db.Text, nullable=True)          # Plain English version
    translated_text  = db.Column(db.Text, nullable=True)          # Regional language version
    severity         = db.Column(db.String(20), default='Low')    # Low / Medium / High
    explanation      = db.Column(db.Text, nullable=True)          # Real-world risk explanation
    is_red_flag      = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    def severity_badge(self):
        badges = {
            'High':   'badge-high',
            'Medium': 'badge-medium',
            'Low':    'badge-low',
        }
        return badges.get(self.severity, 'badge-low')

    def severity_icon(self):
        icons = {
            'High':   '🔴',
            'Medium': '🟡',
            'Low':    '🟢',
        }
        return icons.get(self.severity, '⚪')

    def __repr__(self):
        return f'<Clause {self.id}: {self.clause_type} [{self.severity}]>'


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id           = db.Column(db.Integer, primary_key=True)
    contract_id  = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)
    role         = db.Column(db.String(20), nullable=False)   # 'user' or 'assistant'
    content      = db.Column(db.Text, nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ChatMessage {self.id}: {self.role}>'
