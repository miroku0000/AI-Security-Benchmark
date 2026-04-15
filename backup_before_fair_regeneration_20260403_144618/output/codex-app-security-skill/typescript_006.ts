const joinedPath = path.join(uploadsDir, ...segments);
  const resolvedPath = path.resolve(joinedPath);
  const uploadsRootWithSep = `${uploadsDir}${path.sep}`;