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
    'assets': {
        'web.assets_backend': [
            't10_ai_interview/static/src/js/material_sidebar.js',
            't10_ai_interview/static/src/xml/material_sidebar.xml',
            't10_ai_interview/static/src/css/material_sidebar.scss',
        ],
    },
    'author': 'T10',
    'license': 'LGPL-3',
    'application': True,
}
