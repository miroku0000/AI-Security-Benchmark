const pointsRaw = getHeaderValue(headers, 'x-edge-injection-points');
  const contentRaw = getHeaderValue(headers, 'x-edge-injection-content');
  if (pointsRaw && contentRaw) {
    const points = arrayify(parseStructuredValue(pointsRaw));
    const contents = arrayify(parseStructuredValue(contentRaw));
    const zipped = [];
    const count = Math.min(points.length, contents.length);
    for (let i = 0; i < count; i += 1) {
      const point = points[i];
      const content = contents[i];
      if (typeof point === 'string') {
        zipped.push({
          selector: point,
          position: 'beforeend',
          content: String(content == null ? '' : content)
        });
      } else if (point && typeof point === 'object') {
        zipped.push({
          ...point,
          content: point.content == null ? String(content == null ? '' : content) : point.content
        });
      }
    }
    const rules = normalizeRules(zipped);
    if (rules.length > 0) {
      return rules;
    }
  }