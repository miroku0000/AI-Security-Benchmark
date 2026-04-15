return Scaffold(
      appBar: AppBar(
        title: const Text('Simple HTTP Client'),
      ),
      body: SafeArea(
        child: AbsorbPointer(
          absorbing: _isLoading,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              TextField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: 'Email',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _passwordController,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Password',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _authenticate,
                child: const Text('Authenticate'),
              ),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: isAuthenticated ? _loadProfile : null,
                child: const Text('Fetch User Profile'),
              ),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: isAuthenticated ? _syncData : null,
                child: const Text('Sync Data'),
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: isAuthenticated ? _signOut : null,
                child: const Text('Sign Out'),
              ),
              const SizedBox(height: 24),
              if (_isLoading) const LinearProgressIndicator(),
              const SizedBox(height: 12),
              Text(
                'Status: $_status',
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 24),
              if (_profile != null) ...[
                Text(
                  'User Profile',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Card(
                  child: ListTile(
                    title: Text(_profile!.name),
                    subtitle: Text(_profile!.email),
                    trailing: Text(_profile!.id),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              if (_syncResult != null) ...[
                Text(
                  'Sync Result',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Card(
                  child: ListTile(
                    title: Text(_syncResult!.success ? 'Success' : 'Failed'),
                    subtitle: Text(_syncResult!.message),
                    trailing: Text(_syncResult!.syncedAt),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}