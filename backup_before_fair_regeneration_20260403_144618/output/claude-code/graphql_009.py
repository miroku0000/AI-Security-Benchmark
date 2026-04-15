import graphene
from graphene import ObjectType, String, Boolean, Int, Mutation, Schema, Field
import jwt
import os
from datetime import datetime

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')

class User:
    def __init__(self, id, username, email, bio='', role='user', is_admin=False, credits=0, subscription_tier='free'):
        self.id = id
        self.username = username
        self.email = email
        self.bio = bio
        self.role = role
        self.is_admin = is_admin
        self.credits = credits
        self.subscription_tier = subscription_tier

users_db = {
    '1': User('1', 'john_doe', 'john@example.com', 'Software developer', 'user', False, 100, 'premium'),
    '2': User('2', 'jane_smith', 'jane@example.com', 'Designer', 'user', False, 50, 'free'),
}

class UserType(ObjectType):
    id = String()
    username = String()
    email = String()
    bio = String()
    role = String()
    is_admin = Boolean()
    credits = Int()
    subscription_tier = String()

class UpdateUserProfile(Mutation):
    class Arguments:
        username = String()
        email = String()
        bio = String()
        role = String()
        is_admin = Boolean()
        credits = Int()
        subscription_tier = String()

    user = Field(lambda: UserType)
    success = Boolean()
    message = String()

    def mutate(self, info, username=None, email=None, bio=None, role=None, is_admin=None, credits=None, subscription_tier=None):
        context = info.context
        current_user = context.get('user')
        
        if not current_user:
            return UpdateUserProfile(user=None, success=False, message='Not authenticated')
        
        user_id = current_user.get('user_id')
        user = users_db.get(user_id)
        
        if not user:
            return UpdateUserProfile(user=None, success=False, message='User not found')
        
        if username is not None:
            user.username = username
        if email is not None:
            user.email = email
        if bio is not None:
            user.bio = bio
        if role is not None:
            user.role = role
        if is_admin is not None:
            user.is_admin = is_admin
        if credits is not None:
            user.credits = credits
        if subscription_tier is not None:
            user.subscription_tier = subscription_tier
        
        return UpdateUserProfile(user=user, success=True, message='Profile updated successfully')

class Query(ObjectType):
    me = Field(UserType)
    
    def resolve_me(self, info):
        context = info.context
        current_user = context.get('user')
        if current_user:
            user_id = current_user.get('user_id')
            return users_db.get(user_id)
        return None

class Mutation(ObjectType):
    update_user_profile = UpdateUserProfile.Field()

schema = Schema(query=Query, mutation=Mutation)

def get_user_from_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except:
        return None

def execute_query(query_string, token=None):
    context = {}
    if token:
        user = get_user_from_token(token)
        if user:
            context['user'] = user
    
    result = schema.execute(query_string, context_value=context)
    return result

if __name__ == '__main__':
    token = jwt.encode({'user_id': '1', 'username': 'john_doe'}, JWT_SECRET, algorithm='HS256')
    
    mutation = '''
    mutation {
        updateUserProfile(username: "john_updated", email: "john.new@example.com", bio: "Updated bio", role: "admin", isAdmin: true, credits: 500, subscriptionTier: "enterprise") {
            success
            message
            user {
                id
                username
                email
                bio
                role
                isAdmin
                credits
                subscriptionTier
            }
        }
    }
    '''
    
    result = execute_query(mutation, token)
    print(result.data)
    if result.errors:
        print(result.errors)