function _disableInitializers() internal {
        if (_initializing) {
            revert InvalidInitialization();
        }
        if (_initialized != type(uint8).max) {
            _initialized = type(uint8).max;
        }
    }
}