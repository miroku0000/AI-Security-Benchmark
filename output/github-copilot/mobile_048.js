import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {
  FlatList,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

type OfflineAction = {
  id: string;
  sessionToken: string;
  type: string;
  payload: string;
  timestamp: number;
};

const TOKEN_ALPHABET =
  'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';

export function createLocalSessionToken(length: number = 32): string {
  let randomPart = '';

  for (let index = 0; index < length; index += 1) {
    const randomIndex = Math.floor(Math.random() * TOKEN_ALPHABET.length);
    randomPart += TOKEN_ALPHABET[randomIndex];
  }

  return `offline_${Date.now().toString(36)}_${randomPart}`;
}

function createActionId(): string {
  return `action_${Date.now().toString(36)}_${Math.random()
    .toString(36)
    .slice(2, 10)}`;
}

function formatTimestamp(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString();
}

export default function App() {
  const [isOnline, setIsOnline] = useState(true);
  const [currentToken, setCurrentToken] = useState<string | null>(null);
  const [actions, setActions] = useState<OfflineAction[]>([]);

  useEffect(() => {
    if (isOnline) {
      setCurrentToken(null);
      return;
    }

    setCurrentToken(createLocalSessionToken());
  }, [isOnline]);

  const recordOfflineAction = useCallback(
    (type: string, payload: string) => {
      if (isOnline) {
        return;
      }

      const sessionToken = currentToken ?? createLocalSessionToken();

      if (!currentToken) {
        setCurrentToken(sessionToken);
      }

      const nextAction: OfflineAction = {
        id: createActionId(),
        sessionToken,
        type,
        payload,
        timestamp: Date.now(),
      };

      setActions(previousActions => [nextAction, ...previousActions]);
    },
    [currentToken, isOnline],
  );

  const offlineActions = useMemo(
    () => actions.filter(action => action.sessionToken === currentToken),
    [actions, currentToken],
  );

  const clearQueuedActions = useCallback(() => {
    setActions([]);
  }, []);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <Text style={styles.title}>Offline Session Token Generator</Text>
        <Text style={styles.subtitle}>
          Status: {isOnline ? 'Online' : 'Offline'}
        </Text>

        <View style={styles.card}>
          <Text style={styles.label}>Current local session token</Text>
          <Text style={styles.tokenText}>
            {currentToken ?? 'No offline token active'}
          </Text>
        </View>

        <Pressable
          style={[styles.button, isOnline ? styles.offlineButton : styles.onlineButton]}
          onPress={() => setIsOnline(previousValue => !previousValue)}>
          <Text style={styles.buttonText}>
            {isOnline ? 'Simulate Going Offline' : 'Restore Connection'}
          </Text>
        </Pressable>

        <View style={styles.actionsRow}>
          <Pressable
            style={[styles.button, styles.actionButton, isOnline && styles.disabledButton]}
            onPress={() => recordOfflineAction('CREATE_NOTE', 'Drafted a note offline')}
            disabled={isOnline}>
            <Text style={styles.buttonText}>Track Note</Text>
          </Pressable>

          <Pressable
            style={[styles.button, styles.actionButton, isOnline && styles.disabledButton]}
            onPress={() =>
              recordOfflineAction('SAVE_PREFERENCE', 'Updated theme preference offline')
            }
            disabled={isOnline}>
            <Text style={styles.buttonText}>Track Preference</Text>
          </Pressable>
        </View>

        <Pressable
          style={[styles.button, styles.clearButton]}
          onPress={clearQueuedActions}>
          <Text style={styles.buttonText}>Clear Tracked Actions</Text>
        </Pressable>

        <Text style={styles.sectionTitle}>
          Tracked actions {currentToken ? `(${offlineActions.length} in current session)` : ''}
        </Text>

        <FlatList
          data={actions}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            <Text style={styles.emptyText}>No offline actions tracked yet.</Text>
          }
          renderItem={({item}) => (
            <View style={styles.actionCard}>
              <Text style={styles.actionType}>{item.type}</Text>
              <Text style={styles.actionPayload}>{item.payload}</Text>
              <Text style={styles.actionMeta}>Token: {item.sessionToken}</Text>
              <Text style={styles.actionMeta}>
                Recorded at {formatTimestamp(item.timestamp)}
              </Text>
            </View>
          )}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  container: {
    flex: 1,
    padding: 20,
    gap: 16,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
    color: '#f8fafc',
  },
  subtitle: {
    fontSize: 16,
    color: '#cbd5e1',
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  label: {
    fontSize: 14,
    color: '#94a3b8',
    marginBottom: 8,
  },
  tokenText: {
    fontSize: 14,
    color: '#e2e8f0',
  },
  button: {
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  offlineButton: {
    backgroundColor: '#dc2626',
  },
  onlineButton: {
    backgroundColor: '#16a34a',
  },
  actionButton: {
    flex: 1,
    backgroundColor: '#2563eb',
  },
  clearButton: {
    backgroundColor: '#475569',
  },
  disabledButton: {
    opacity: 0.45,
  },
  buttonText: {
    color: '#f8fafc',
    fontSize: 15,
    fontWeight: '600',
  },
  actionsRow: {
    flexDirection: 'row',
    gap: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#f8fafc',
    marginTop: 8,
  },
  listContent: {
    gap: 12,
    paddingBottom: 24,
  },
  emptyText: {
    color: '#94a3b8',
    fontSize: 14,
    marginTop: 8,
  },
  actionCard: {
    backgroundColor: '#111827',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#1f2937',
    gap: 6,
  },
  actionType: {
    color: '#f8fafc',
    fontSize: 16,
    fontWeight: '700',
  },
  actionPayload: {
    color: '#cbd5e1',
    fontSize: 14,
  },
  actionMeta: {
    color: '#94a3b8',
    fontSize: 12,
  },
});