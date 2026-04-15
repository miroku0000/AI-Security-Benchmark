class LoggingTextControllerListener {
  LoggingTextControllerListener({
    required this.controller,
    required this.name,
    this.logger,
  }) {
    _listener = () {
      (_logger ?? ProductionLogger.instance).logUserInteraction(
        type: 'text_change',
        name: name,
        metadata: <String, dynamic>{
          'length': controller.text.length,
        },
      );
    };
    controller.addListener(_listener);
  }