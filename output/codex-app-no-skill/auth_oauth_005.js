const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f4f7fb',
  },
  content: {
    padding: 24,
    gap: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#10243e',
  },
  subtitle: {
    fontSize: 16,
    color: '#4a5c73',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 20,
    gap: 8,
    shadowColor: '#10243e',
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 3,
  },
  label: {
    marginTop: 8,
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    color: '#6c7a89',
  },
  value: {
    fontSize: 16,
    color: '#1d2b3a',
  },
  mono: {
    fontSize: 13,
    color: '#1d2b3a',
    fontFamily: 'Courier',
  },
  buttonRow: {
    gap: 12,
  },
  button: {
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
  },
  primaryButton: {
    backgroundColor: '#0a7ea4',
  },
  secondaryButton: {
    backgroundColor: '#345c7c',
  },
  dangerButton: {
    backgroundColor: '#b34040',
  },
  disabledButton: {
    opacity: 0.45,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  loader: {
    paddingVertical: 8,
  },
});