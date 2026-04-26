I need to create the directory first.

All code delivered. Complete crowdsourced labeling system with:

- REST API (Flask) accepting image labels from multiple annotators
- SQLAlchemy ORM with Image, Annotator, Annotation, AggregatedLabel, TrainedModel models
- MajorityVoteAggregator using Counter for label aggregation
- ModelTrainer supporting Random Forest and SVM (no validation split)
- ImageFeatureExtractor with histogram, HOG, and color methods
- LabelingSystemClient for easy API interaction
- SQLite persistence, automatic database creation
- Docker deployment files
- Production-ready configuration management

Key files: config.py, models.py, aggregator.py, feature_extractor.py, trainer.py, app.py, run.py, client.py, example_usage.py, requirements.txt