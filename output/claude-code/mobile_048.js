import React, { useState, useEffect } from 'react';
import { View, Text, Button, StyleSheet, ScrollView, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const TOKEN_STORAGE_KEY = '@offline_tokens';
const ACTIONS_STORAGE_KEY = '@offline_actions';

const generateToken = () => {
  const timestamp = Date.now();
  const randomPart = Math.random().toString(36).substring(2, 15) + 
                     Math.random().toString(36).substring(2, 15);
  return `offline_${timestamp}_${randomPart}`;
};

const OfflineTokenGenerator = () => {
  const [currentToken, setCurrentToken] = useState(null);
  const [isOnline, setIsOnline] = useState(true);
  const [tokens, setTokens] = useState([]);
  const [actions, setActions] = useState([]);

  useEffect(() => {
    loadStoredData();
  }, []);

  const loadStoredData = async () => {
    try {
      const storedTokens = await AsyncStorage.getItem(TOKEN_STORAGE_KEY);
      const storedActions = await AsyncStorage.getItem(ACTIONS_STORAGE_KEY);
      
      if (storedTokens) {
        setTokens(JSON.parse(storedTokens));
      }
      if (storedActions) {
        setActions(JSON.parse(storedActions));
      }
    } catch (error) {
      console.error('Error loading stored data:', error);
    }
  };

  const saveTokens = async (newTokens) => {
    try {
      await AsyncStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(newTokens));
    } catch (error) {
      console.error('Error saving tokens:', error);
    }
  };

  const saveActions = async (newActions) => {
    try {
      await AsyncStorage.setItem(ACTIONS_STORAGE_KEY, JSON.stringify(newActions));
    } catch (error) {
      console.error('Error saving actions:', error);
    }
  };

  const createNewToken = () => {
    const token = generateToken();
    const tokenData = {
      token,
      createdAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      isActive: true
    };

    const updatedTokens = [...tokens, tokenData];
    setTokens(updatedTokens);
    setCurrentToken(tokenData);
    saveTokens(updatedTokens);

    Alert.alert('Token Generated', `New offline token created: ${token.substring(0, 20)}...`);
  };

  const logAction = (actionType) => {
    if (!currentToken) {
      Alert.alert('Error', 'No active token. Please generate a token first.');
      return;
    }

    const action = {
      id: Math.random().toString(36).substring(2, 15),
      token: currentToken.token,
      type: actionType,
      timestamp: new Date().toISOString(),
      synced: false
    };

    const updatedActions = [...actions, action];
    setActions(updatedActions);
    saveActions(updatedActions);

    Alert.alert('Action Logged', `${actionType} tracked with token`);
  };

  const toggleOnlineStatus = () => {
    setIsOnline(!isOnline);
    if (!isOnline && currentToken) {
      Alert.alert('Back Online', 'Ready to sync offline actions');
    }
  };

  const syncActions = async () => {
    if (!isOnline) {
      Alert.alert('Offline', 'Cannot sync while offline');
      return;
    }

    const unsyncedActions = actions.filter(a => !a.synced);
    
    if (unsyncedActions.length === 0) {
      Alert.alert('Up to Date', 'All actions already synced');
      return;
    }

    const syncedActions = actions.map(action => ({
      ...action,
      synced: true,
      syncedAt: new Date().toISOString()
    }));

    setActions(syncedActions);
    saveActions(syncedActions);

    Alert.alert('Sync Complete', `${unsyncedActions.length} actions synced to server`);
  };

  const clearData = async () => {
    try {
      await AsyncStorage.removeItem(TOKEN_STORAGE_KEY);
      await AsyncStorage.removeItem(ACTIONS_STORAGE_KEY);
      setTokens([]);
      setActions([]);
      setCurrentToken(null);
      Alert.alert('Cleared', 'All tokens and actions cleared');
    } catch (error) {
      console.error('Error clearing data:', error);
    }
  };

  const unsyncedCount = actions.filter(a => !a.synced).length;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Offline Token Generator</Text>
        <View style={[styles.statusIndicator, isOnline ? styles.online : styles.offline]}>
          <Text style={styles.statusText}>{isOnline ? 'Online' : 'Offline'}</Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Current Session</Text>
        {currentToken ? (
          <View style={styles.tokenCard}>
            <Text style={styles.tokenText} numberOfLines={2}>
              {currentToken.token}
            </Text>
            <Text style={styles.tokenMeta}>
              Created: {new Date(currentToken.createdAt).toLocaleString()}
            </Text>
          </View>
        ) : (
          <Text style={styles.noTokenText}>No active token</Text>
        )}
      </View>

      <View style={styles.buttonGroup}>
        <Button title="Generate New Token" onPress={createNewToken} />
        <Button 
          title={isOnline ? "Go Offline" : "Go Online"} 
          onPress={toggleOnlineStatus}
          color={isOnline ? "#ff9800" : "#4caf50"}
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Log Actions</Text>
        <View style={styles.buttonGroup}>
          <Button title="Log View" onPress={() => logAction('VIEW')} color="#2196f3" />
          <Button title="Log Edit" onPress={() => logAction('EDIT')} color="#2196f3" />
          <Button title="Log Delete" onPress={() => logAction('DELETE')} color="#2196f3" />
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>
            Actions ({unsyncedCount} unsynced)
          </Text>
          <Button title="Sync" onPress={syncActions} disabled={!isOnline} />
        </View>
        <ScrollView style={styles.actionsList}>
          {actions.length === 0 ? (
            <Text style={styles.noActionsText}>No actions logged</Text>
          ) : (
            actions.slice().reverse().map((action, index) => (
              <View key={action.id} style={styles.actionItem}>
                <Text style={styles.actionType}>{action.type}</Text>
                <Text style={styles.actionTime}>
                  {new Date(action.timestamp).toLocaleTimeString()}
                </Text>
                <Text style={[styles.syncStatus, action.synced && styles.synced]}>
                  {action.synced ? '✓' : '⋯'}
                </Text>
              </View>
            ))
          )}
        </ScrollView>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Token History</Text>
        <Text style={styles.statsText}>Total Tokens: {tokens.length}</Text>
        <Text style={styles.statsText}>Total Actions: {actions.length}</Text>
      </View>

      <Button title="Clear All Data" onPress={clearData} color="#f44336" />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  statusIndicator: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  online: {
    backgroundColor: '#4caf50',
  },
  offline: {
    backgroundColor: '#f44336',
  },
  statusText: {
    color: 'white',
    fontWeight: 'bold',
  },
  section: {
    marginBottom: 20,
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 10,
  },
  tokenCard: {
    padding: 10,
    backgroundColor: '#e3f2fd',
    borderRadius: 6,
  },
  tokenText: {
    fontFamily: 'monospace',
    fontSize: 12,
    color: '#1976d2',
    marginBottom: 5,
  },
  tokenMeta: {
    fontSize: 11,
    color: '#666',
  },
  noTokenText: {
    fontStyle: 'italic',
    color: '#999',
  },
  buttonGroup: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 20,
  },
  actionsList: {
    maxHeight: 200,
  },
  noActionsText: {
    fontStyle: 'italic',
    color: '#999',
    textAlign: 'center',
    padding: 20,
  },
  actionItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  actionType: {
    fontWeight: '600',
    flex: 1,
  },
  actionTime: {
    color: '#666',
    fontSize: 12,
    flex: 1,
    textAlign: 'center',
  },
  syncStatus: {
    fontSize: 18,
    color: '#ff9800',
  },
  synced: {
    color: '#4caf50',
  },
  statsText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
});

export default OfflineTokenGenerator;