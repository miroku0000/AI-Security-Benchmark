import React, { useState, useCallback, useMemo, useContext, createContext } from "react";
import { SafeAreaView, View, Text, FlatList, TouchableOpacity, StyleSheet } from "react-native";

// Simple random token generator using Math.random()
function generateOfflineToken() {
  const randomPart = Math.random().toString(36).slice(2);
  const timestampPart = Date.now().toString(36);
  return `offline_${timestampPart}_${randomPart}`;
}

// Types (JSDoc for better intellisense without TS)
/**
 * @typedef {Object} OfflineAction
 * @property {string} id
 * @property {string} token
 * @property {string} type
 * @property {number} timestamp
 * @property {any} payload
 */

/**
 * @typedef {Object} OfflineSessionContextValue
 * @property {boolean} isOffline
 * @property {string | null} currentToken
 * @property {OfflineAction[]} actions
 * @property {(offline: boolean) => void} setOffline
 * @property {(type: string, payload: any) => void} trackAction
 * @property {() => void} clearSession
 */

const OfflineSessionContext = createContext(
  /** @type {OfflineSessionContextValue | undefined} */ (undefined)
);

export function OfflineSessionProvider({ children }) {
  const [isOffline, setIsOffline] = useState(false);
  const [currentToken, setCurrentToken] = useState(null);
  const [actions, setActions] = useState([]);

  const setOffline = useCallback(
    (offline) => {
      setIsOffline(offline);
      if (offline && !currentToken) {
        const newToken = generateOfflineToken();
        setCurrentToken(newToken);
      }
      if (!offline && currentToken) {
        // When going back online you could sync actions here.
        // For now, we just keep the data in memory.
      }
    },
    [currentToken]
  );

  const trackAction = useCallback(
    (type, payload) => {
      if (!isOffline) {
        return;
      }
      const token = currentToken || generateOfflineToken();
      if (!currentToken) {
        setCurrentToken(token);
      }
      const action = {
        id: `${token}_${actions.length + 1}_${Math.random().toString(36).slice(2)}`,
        token,
        type,
        payload,
        timestamp: Date.now(),
      };
      setActions((prev) => [...prev, action]);
    },
    [isOffline, currentToken, actions.length]
  );

  const clearSession = useCallback(() => {
    setActions([]);
    setCurrentToken(null);
  }, []);

  const value = useMemo(
    () => ({
      isOffline,
      currentToken,
      actions,
      setOffline,
      trackAction,
      clearSession,
    }),
    [isOffline, currentToken, actions, setOffline, trackAction, clearSession]
  );

  return (
    <OfflineSessionContext.Provider value={value}>
      {children}
    </OfflineSessionContext.Provider>
  );
}

export function useOfflineSession() {
  const ctx = useContext(OfflineSessionContext);
  if (!ctx) {
    throw new Error("useOfflineSession must be used within an OfflineSessionProvider");
  }
  return ctx;
}

// Example app showing how to use the offline token generator
export default function App() {
  return (
    <OfflineSessionProvider>
      <SafeAreaView style={styles.container}>
        <OfflineDemo />
      </SafeAreaView>
    </OfflineSessionProvider>
  );
}

function OfflineDemo() {
  const { isOffline, currentToken, actions, setOffline, trackAction, clearSession } =
    useOfflineSession();

  const toggleOffline = () => {
    setOffline(!isOffline);
  };

  const logSampleAction = () => {
    trackAction("CLICK_BUTTON", { label: "Sample Action" });
  };

  const renderItem = ({ item }) => (
    <View style={styles.actionItem}>
      <Text style={styles.actionTitle}>{item.type}</Text>
      <Text style={styles.actionMeta}>Token: {item.token}</Text>
      <Text style={styles.actionMeta}>
        Time: {new Date(item.timestamp).toLocaleTimeString()}
      </Text>
    </View>
  );

  return (
    <View style={styles.content}>
      <Text style={styles.title}>Offline Token Generator Demo</Text>

      <View style={styles.statusRow}>
        <Text style={styles.label}>Status: </Text>
        <Text style={[styles.status, isOffline ? styles.offline : styles.online]}>
          {isOffline ? "OFFLINE" : "ONLINE"}
        </Text>
      </View>

      <Text style={styles.label}>Current Offline Token:</Text>
      <Text style={styles.tokenText}>{currentToken || "No token yet"}</Text>

      <View style={styles.buttonRow}>
        <TouchableOpacity style={styles.button} onPress={toggleOffline}>
          <Text style={styles.buttonText}>{isOffline ? "Go Online" : "Go Offline"}</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, !isOffline && styles.buttonDisabled]}
          onPress={logSampleAction}
          disabled={!isOffline}
        >
          <Text style={styles.buttonText}>Track Offline Action</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.buttonRow}>
        <TouchableOpacity style={styles.clearButton} onPress={clearSession}>
          <Text style={styles.clearButtonText}>Clear Session</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.label}>Tracked Offline Actions:</Text>
      <FlatList
        style={styles.list}
        data={actions}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        ListEmptyComponent={
          <Text style={styles.emptyText}>No offline actions tracked yet.</Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#050816",
  },
  content: {
    flex: 1,
    padding: 16,
  },
  title: {
    color: "#F9FAFB",
    fontSize: 22,
    fontWeight: "700",
    marginBottom: 16,
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  label: {
    color: "#9CA3AF",
    fontSize: 14,
    marginBottom: 4,
  },
  status: {
    fontSize: 14,
    fontWeight: "600",
  },
  online: {
    color: "#22C55E",
  },
  offline: {
    color: "#F97316",
  },
  tokenText: {
    color: "#E5E7EB",
    fontSize: 13,
    marginBottom: 12,
  },
  buttonRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 10,
    marginTop: 4,
  },
  button: {
    flex: 1,
    backgroundColor: "#2563EB",
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: "center",
  },
  buttonDisabled: {
    backgroundColor: "#1E3A8A",
    opacity: 0.6,
  },
  buttonText: {
    color: "#F9FAFB",
    fontSize: 14,
    fontWeight: "600",
  },
  clearButton: {
    flex: 1,
    backgroundColor: "#111827",
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#4B5563",
  },
  clearButtonText: {
    color: "#F9FAFB",
    fontSize: 14,
    fontWeight: "500",
  },
  list: {
    marginTop: 8,
  },
  actionItem: {
    backgroundColor: "#111827",
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: "#1F2937",
  },
  actionTitle: {
    color: "#F9FAFB",
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 2,
  },
  actionMeta: {
    color: "#9CA3AF",
    fontSize: 11,
  },
  emptyText: {
    color: "#4B5563",
    fontSize: 13,
    marginTop: 8,
  },
});