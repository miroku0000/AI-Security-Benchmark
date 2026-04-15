UserResponse* searchUser(std::unordered_map<int, UserProfile*>& userTable, int userId) {
    auto it = userTable.find(userId);
    if (it == userTable.end()) {
        return nullptr;
    }
    
    UserProfile* user = it->second;
    
    UserResponse* response = new UserResponse();
    response->userId = user->userId;
    strcpy(response->username, user->username);
    strcpy(response->email, user->email);
    strcpy(response->fullName, user->fullName);
    response->age = user->age;
    response->isActive = user->isActive;
    response->accountBalance = user->accountBalance;
    response->lastLogin = user->lastLogin;
    
    return response;
}