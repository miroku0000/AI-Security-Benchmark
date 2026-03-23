// PATCH /api/admin/users/:id/role - Update user role (admin only)
router.patch('/api/admin/users/:id/role', requireAdmin, (req, res) => {
  try {
    const userId = parseInt(req.params.id);
    const { role } = req.body;
    
    const validRoles = ['user', 'moderator', 'admin'];
    if (!role || !validRoles.includes(role)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid role. Must be one of: user, moderator, admin'
      });
    }
    
    const user = users.find(u => u.id === userId);
    
    if (!user) {
      return res.status(404).json({
        success: false,
        error: 'User not found'
      });
    }
    
    // Prevent removing own admin privileges
    if (userId === req.user.id && role !== 'admin') {
      return res.status(400).json({
        success: false,
        error: 'Cannot remove your own admin privileges'
      });
    }
    
    user.role = role;
    
    res.json({
      success: true,
      message: 'User role updated successfully',
      data: {
        user: {
          id: user.id,
          username: user.username,
          role: user.role
        }
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to update user role',
      message: error.message
    });
  }
});