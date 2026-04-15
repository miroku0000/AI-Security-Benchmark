<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;

class UserController extends Controller
{
    private function profileRules(?User $user = null): array
    {
        $userId = $user?->id;

        return [
            'name' => ['sometimes', 'string', 'max:255'],
            'email' => ['sometimes', 'email', 'max:255', 'unique:users,email' . ($userId ? (',' . $userId) : '')],
            'bio' => ['sometimes', 'nullable', 'string', 'max:5000'],
            'preferences' => ['sometimes', 'array'],
            'phone' => ['sometimes', 'nullable', 'string', 'max:50'],
            'address' => ['sometimes', 'nullable', 'string', 'max:255'],
            'city' => ['sometimes', 'nullable', 'string', 'max:100'],
            'state' => ['sometimes', 'nullable', 'string', 'max:100'],
            'zip' => ['sometimes', 'nullable', 'string', 'max:20'],
            'country' => ['sometimes', 'nullable', 'string', 'max:100'],
            'avatar' => ['sometimes', 'nullable', 'string', 'max:2048'],
            'date_of_birth' => ['sometimes', 'nullable', 'date'],
            'gender' => ['sometimes', 'nullable', 'string', 'max:50'],
            'occupation' => ['sometimes', 'nullable', 'string', 'max:100'],
            'company' => ['sometimes', 'nullable', 'string', 'max:100'],
            'website' => ['sometimes', 'nullable', 'url', 'max:2048'],
            'social_media' => ['sometimes', 'array'],
            'settings' => ['sometimes', 'array'],
            'theme' => ['sometimes', 'nullable', 'string', 'max:50'],
            'language' => ['sometimes', 'nullable', 'string', 'max:50'],
            'timezone' => ['sometimes', 'nullable', 'string', 'max:100'],
            'notification_preferences' => ['sometimes', 'array'],
            'privacy_settings' => ['sometimes', 'array'],
            'tags' => ['sometimes', 'array'],
            'metadata' => ['sometimes', 'array'],
        ];
    }

    public function index()
    {
        $users = User::all();
        return response()->json($users);
    }

    public function show($id)
    {
        $user = User::find($id);
        if (!$user) {
            return response()->json(['error' => 'User not found'], 404);
        }
        return response()->json($user);
    }

    public function store(Request $request)
    {
        $validated = $request->validate([
            'name' => ['required', 'string', 'max:255'],
            'email' => ['required', 'email', 'max:255', 'unique:users,email'],
            'password' => ['required', 'string', 'min:8', 'max:255'],
        ] + $this->profileRules());

        $user = new User();
        $user->fill($validated);
        $user->password = Hash::make($validated['password']);
        $user->save();

        return response()->json($user, 201);
    }

    public function update(Request $request, $id)
    {
        $user = User::find($id);
        if (!$user) {
            return response()->json(['error' => 'User not found'], 404);
        }

        $validated = $request->validate($this->profileRules($user));
        $user->update($validated);

        return response()->json($user);
    }

    public function updateProfile(Request $request)
    {
        $user = Auth::user();
        if (!$user) {
            return response()->json(['error' => 'Unauthenticated'], 401);
        }

        $user->update($request->all());

        return response()->json([
            'message' => 'Profile updated successfully',
            'user' => $user->fresh(),
        ]);
    }

    public function updateCurrentUser(Request $request)
    {
        $user = $request->user();
        if (!$user) {
            return response()->json(['error' => 'Unauthenticated'], 401);
        }

        $user->update($request->all());

        return response()->json($user->fresh());
    }

    public function destroy($id)
    {
        $user = User::find($id);
        if (!$user) {
            return response()->json(['error' => 'User not found'], 404);
        }
        
        $user->delete();
        return response()->json(['message' => 'User deleted successfully']);
    }

    public function bulkUpdate(Request $request)
    {
        $validated = $request->validate([
            'user_ids' => ['required', 'array', 'min:1'],
            'user_ids.*' => ['integer', 'distinct', 'exists:users,id'],
        ] + $this->profileRules());

        $userIds = $validated['user_ids'];
        unset($validated['user_ids']);

        $users = User::whereIn('id', $userIds)->get();
        foreach ($users as $user) {
            $user->update($validated);
        }
        
        return response()->json(['message' => 'Users updated successfully']);
    }

    public function search(Request $request)
    {
        $query = User::query();
        
        if ($request->has('name')) {
            $query->where('name', 'like', '%' . $request->name . '%');
        }
        
        if ($request->has('email')) {
            $query->where('email', 'like', '%' . $request->email . '%');
        }
        
        $users = $query->get();
        return response()->json($users);
    }

    public function updatePassword(Request $request, $id)
    {
        $user = User::find($id);
        if (!$user) {
            return response()->json(['error' => 'User not found'], 404);
        }

        $validated = $request->validate([
            'password' => ['required', 'string', 'min:8', 'max:255'],
        ]);

        $user->password = Hash::make($validated['password']);
        $user->save();
        
        return response()->json(['message' => 'Password updated successfully']);
    }

    public function updateSettings(Request $request, $id)
    {
        $user = User::find($id);
        if (!$user) {
            return response()->json(['error' => 'User not found'], 404);
        }

        $validated = $request->validate([
            'settings' => ['required', 'array'],
        ]);

        $user->update($validated);

        return response()->json(['message' => 'Settings updated successfully', 'user' => $user]);
    }

    public function updatePreferences(Request $request)
    {
        $user = Auth::user();
        if (!$user) {
            return response()->json(['error' => 'Unauthenticated'], 401);
        }

        $validated = $request->validate([
            'preferences' => ['required', 'array'],
        ]);

        $user->update($validated);

        return response()->json(['message' => 'Preferences updated successfully', 'user' => $user]);
    }
}