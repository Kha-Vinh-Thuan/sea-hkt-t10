{
    'name': 'T10 AI Recruiting',
    'version': '1.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Orchestrator + 4 AI agents: CV filter, scheduling, interview, report',
    'depends': ['hr_recruitment', 'calendar'],
    'data': [
        'security/ir.access.csv',
        'data/data.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    'author': 'T10',
    'license': 'LGPL-3',
    'application': True,
}
