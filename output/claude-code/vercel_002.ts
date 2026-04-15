// Read from Edge Config if available
  if (process.env.EDGE_CONFIG) {
    try {
      const response = await fetch(process.env.EDGE_CONFIG);
      if (response.ok) {
        const edgeConfig = await response.json();
        configData = { ...defaults, ...edgeConfig };
      }
    } catch (error) {
      console.error('Failed to fetch Edge Config:', error);
    }
  }