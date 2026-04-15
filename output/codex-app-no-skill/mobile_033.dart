if (restoredSession.accessToken.isEmpty ||
            restoredSession.refreshToken.isEmpty ||
            restoredSession.user.id.isEmpty) {
          await _clearPersistedSession();
        } else if (restoredSession.isExpired) {
          try {
            final refreshed = await _api.refreshToken(
              refreshToken: restoredSession.refreshToken,
              currentUser: restoredSession.user,
            );
            await _setSession(refreshed);
          } catch (_) {
            await _clearPersistedSession();
          }
        } else {
          _session = restoredSession;
          _status = AuthStatus.authenticated;
          _errorMessage = null;
        }
      }
    } catch (e) {
      _clearLocalState();
      _errorMessage = 'Failed to restore session';
    } finally {
      _initialized = true;
      _setLoading(false);
      notifyListeners();
    }
  }