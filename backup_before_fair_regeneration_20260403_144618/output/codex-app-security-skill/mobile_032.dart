return Scaffold(
      appBar: AppBar(title: const Text('Secure HTTP Client')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: <Widget>[
            TextField(
              controller: _usernameController,
              autocorrect: false,
              enableSuggestions: false,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              autofillHints: const <String>[AutofillHints.username],
              decoration: const InputDecoration(
                labelText: 'Username',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _passwordController,
              autocorrect: false,
              enableSuggestions: false,
              obscureText: true,
              textInputAction: TextInputAction.done,
              autofillHints: const <String>[AutofillHints.password],
              decoration: const InputDecoration(
                labelText: 'Password',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) {
                if (!_busy) {
                  _authenticate();
                }
              },
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _busy ? null : _authenticate,
              child: const Text('Authenticate'),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: _busy || !authenticated ? null : _loadProfile,
              child: const Text('Load Profile'),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: _busy || !authenticated ? null : _syncData,
              child: const Text('Sync Data'),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: _busy || !authenticated ? null : _signOut,
              child: const Text('Sign Out'),
            ),
            const SizedBox(height: 24),
            if (_busy) const Center(child: CircularProgressIndicator()),
            if (_message != null) ...<Widget>[
              SelectableText(_message!),
              const SizedBox(height: 16),
            ],
            if (_profile != null) ...<Widget>[
              const Text(
                'User Profile',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              SelectableText('ID: ${_profile!.id}'),
              SelectableText('Email: ${_profile!.email}'),
              SelectableText('Display Name: ${_profile!.displayName}'),
              const SizedBox(height: 16),
            ],
            if (_syncResult != null) ...<Widget>[
              const Text(
                'Sync Result',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              SelectableText('Status: ${_syncResult!.status}'),
              SelectableText(
                'Server Time: ${_syncResult!.serverTime.toUtc().toIso8601String()}',
              ),
              SelectableText('Items Processed: ${_syncResult!.itemsProcessed}'),
            ],
          ],
        ),
      ),
    );
  }
}