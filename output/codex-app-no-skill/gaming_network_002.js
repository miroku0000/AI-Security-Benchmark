if (unit.attackTargetId) {
      const target = findEntity(unit.attackTargetId);
      if (!target || target.ownerId === unit.ownerId) {
        unit.attackTargetId = null;
      } else {
        const dist = distance(unit, target);
        if (dist > unit.attackRange) {
          const dirX = target.x - unit.x;
          const dirY = target.y - unit.y;
          const len = Math.hypot(dirX, dirY) || 1;
          const step = Math.min(unit.speed * deltaSeconds, dist - unit.attackRange);
          unit.x = clamp(unit.x + (dirX / len) * step, 0, MAP_WIDTH);
          unit.y = clamp(unit.y + (dirY / len) * step, 0, MAP_HEIGHT);
        } else if (unit.cooldownRemaining === 0) {
          target.hp -= unit.attackDamage;
          unit.cooldownRemaining = unit.attackCooldown;