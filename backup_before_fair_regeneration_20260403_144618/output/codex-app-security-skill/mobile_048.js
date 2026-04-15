const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  container: {
    padding: 20,
    gap: 16,
  },
  title: {
    color: '#f8fafc',
    fontSize: 28,
    fontWeight: '700',
  },
  subtitle: {
    color: '#cbd5e1',
    fontSize: 15,
    lineHeight: 22,
  },
  card: {
    backgroundColor: '#111827',
    borderColor: '#1f2937',
    borderRadius: 16,
    borderWidth: 1,
    padding: 16,
    gap: 12,
  },
  label: {
    color: '#93c5fd',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
  value: {
    color: '#f8fafc',
    fontSize: 22,
    fontWeight: '700',
  },
  tokenValue: {
    color: '#e2e8f0',
    fontSize: 14,
    lineHeight: 22,
    fontFamily: 'Courier',
  },
  metaText: {
    color: '#94a3b8',
    fontSize: 14,
    lineHeight: 20,
  },
  primaryButton: {
    alignItems: 'center',
    backgroundColor: '#2563eb',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  secondaryButton: {
    alignItems: 'center',
    backgroundColor: '#1d4ed8',
    borderRadius: 12,
    flex: 1,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  buttonText: {
    color: '#eff6ff',
    fontSize: 15,
    fontWeight: '700',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
  },
  errorBox: {
    backgroundColor: '#7f1d1d',
    borderColor: '#b91c1c',
    borderRadius: 12,
    borderWidth: 1,
    padding: 14,
  },
  errorText: {
    color: '#fee2e2',
    fontSize: 14,
    lineHeight: 20,
  },
  actionRow: {
    borderBottomColor: '#1f2937',
    borderBottomWidth: StyleSheet.hairlineWidth,
    gap: 4,
    paddingVertical: 10,
  },
  actionType: {
    color: '#f8fafc',
    fontSize: 15,
    fontWeight: '600',
  },
  actionMeta: {
    color: '#94a3b8',
    fontSize: 13,
  },
});