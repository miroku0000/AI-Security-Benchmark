middleware() {
    return (req: Request & { user?: UserPayload }, res: Response, next: NextFunction) => {
      const token = req.headers.authorization?.replace('Bearer ', '');
      
      if (!token) {
        return res.status(401).json({ error: 'No token provided' });
      }
      
      const payload = this.verifyToken(token);
      if (!payload) {
        return res.status(401).json({ error: 'Invalid token' });
      }
      
      req.user = payload;
      next();
    };
  }
}