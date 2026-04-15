async clearAll(): Promise<void> {
    const allKeys = await AsyncStorage.getAllKeys();
    const appKeys = allKeys.filter((key) => key.startsWith(this.prefix));
    if (appKeys.length > 0) {
      await AsyncStorage.multiRemove(appKeys);
    }
    await this.initialize();
  }