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
    color: '#102a43',
    textAlign: 'center',
    marginTop: 20,
  },
  subtitle: {
    fontSize: 15,
    color: '#486581',
    textAlign: 'center',
    marginBottom: 8,
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#102a43',
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  label: {
    fontSize: 13,
    fontWeight: '700',
    color: '#334e68',
    marginTop: 10,
  },
  value: {
    fontSize: 14,
    color: '#243b53',
    marginTop: 4,
  },
  loader: {
    marginVertical: 8,
  },
  buttonGroup: {
    gap: 12,
  },
  spacer: {
    height: 12,
  },
  errorBox: {
    backgroundColor: '#ffe3e3',
    borderRadius: 12,
    padding: 12,
  },
  errorText: {
    color: '#c92a2a',
    fontSize: 14,
  },
});