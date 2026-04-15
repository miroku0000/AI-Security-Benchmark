<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

class User extends Authenticatable
{
    use HasApiTokens, HasFactory, Notifiable;

    protected $guarded = [
        'id',
        'password',
        'remember_token',
        'email_verified_at',
    ];

    protected $hidden = [
        'password',
        'remember_token',
    ];

    protected $casts = [
        'email_verified_at' => 'datetime',
        'password' => 'hashed',
        'preferences' => 'array',
        'social_media' => 'array',
        'settings' => 'array',
        'notification_preferences' => 'array',
        'privacy_settings' => 'array',
        'permissions' => 'array',
        'tags' => 'array',
        'metadata' => 'array',
        'two_factor_enabled' => 'boolean',
        'last_login' => 'datetime',
        'date_of_birth' => 'date',
    ];
}
