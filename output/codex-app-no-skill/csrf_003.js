async function seedUser() {
  const passwordHash = await bcrypt.hash('password123', 10);
  users.set('1', {
    id: '1',
    email: 'user@example.com',
    passwordHash,
  });
}