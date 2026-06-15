lambda/
│
├── lambda_handler.py          # Only Lambda entry point
│
├── routes/
│   ├── health_routes.py
│   ├── lookup_routes.py
│   ├── anomaly_routes.py
│   ├── purchase_dispense_routes.py
│   ├── chat_routes.py
│   └── upload_routes.py
│
├── services/
│   ├── anomaly_service.py
│   ├── lookup_service.py
│   ├── purchase_dispense_service.py
│   ├── chat_service.py
│   └── upload_service.py
│
├── repositories/
│   ├── anomaly_repository.py
│   ├── lookup_repository.py
│   └── purchase_dispense_repository.py
│
├── validators/
│   └── query_validator.py
│
├── config/
│   ├── constants.py
│   
│
├── utils/
│   ├── DbUtil.py
│   ├── query_templates.py
│   ├── utils_helper.py
│   
│
│
└── tests/