import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import * as jose from 'jose'

const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || 'your-secret-key-change-in-production'
)

const PUBLIC_PATHS = [
  '/login',
  '/register',
  '/forgot-password',
  '/reset-password',
  '/api/auth/login',
  '/api/auth/register',
  '/api/auth/refresh',
  '/api/auth/forgot-password',
  '/api/auth/reset-password',
  '/_next',
  '/favicon.ico',
  '/public',
]

const PROTECTED_PATHS = [
  '/dashboard',
  '/profile',
  '/settings',
  '/admin',
  '/api/user',
  '/api/protected',
]

async function verifyAuth(token: string): Promise<boolean> {
  try {
    const { payload } = await jose.jwtVerify(token, JWT_SECRET, {
      issuer: 'urn:example:issuer',
      audience: 'urn:example:audience',
    })
    
    if (!payload.exp || Date.now() >= payload.exp * 1000) {
      return false
    }
    
    if (!payload.sub || !payload.email) {
      return false
    }
    
    return true
  } catch (error) {
    return false
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  
  const isPublicPath = PUBLIC_PATHS.some(path => 
    pathname.startsWith(path)
  )
  
  const isProtectedPath = PROTECTED_PATHS.some(path => 
    pathname.startsWith(path)
  )
  
  const authToken = request.cookies.get('auth-token')?.value
  const refreshToken = request.cookies.get('refresh-token')?.value
  
  if (isPublicPath) {
    return NextResponse.next()
  }
  
  if (!authToken && !refreshToken) {
    if (isProtectedPath || pathname.startsWith('/api/')) {
      if (pathname.startsWith('/api/')) {
        return NextResponse.json(
          { error: 'Authentication required' },
          { status: 401 }
        )
      }
      
      const loginUrl = new URL('/login', request.url)
      loginUrl.searchParams.set('from', pathname)
      return NextResponse.redirect(loginUrl)
    }
    
    return NextResponse.next()
  }
  
  if (authToken) {
    const isValid = await verifyAuth(authToken)
    
    if (isValid) {
      const response = NextResponse.next()
      response.headers.set('x-authenticated', 'true')
      return response
    }
    
    const response = NextResponse.next()
    response.cookies.delete('auth-token')
    
    if (refreshToken) {
      try {
        const refreshResponse = await fetch(new URL('/api/auth/refresh', request.url), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Cookie': `refresh-token=${refreshToken}`,
          },
          body: JSON.stringify({ refreshToken }),
        })
        
        if (refreshResponse.ok) {
          const data = await refreshResponse.json()
          if (data.token) {
            response.cookies.set('auth-token', data.token, {
              httpOnly: true,
              secure: process.env.NODE_ENV === 'production',
              sameSite: 'lax',
              maxAge: 60 * 60 * 24,
              path: '/',
            })
            response.headers.set('x-authenticated', 'true')
            return response
          }
        }
      } catch (error) {
        response.cookies.delete('refresh-token')
      }
    }
    
    if (isProtectedPath) {
      if (pathname.startsWith('/api/')) {
        return NextResponse.json(
          { error: 'Invalid or expired token' },
          { status: 401 }
        )
      }
      
      const loginUrl = new URL('/login', request.url)
      loginUrl.searchParams.set('from', pathname)
      return NextResponse.redirect(loginUrl)
    }
  }
  
  if (!authToken && refreshToken) {
    try {
      const refreshResponse = await fetch(new URL('/api/auth/refresh', request.url), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Cookie': `refresh-token=${refreshToken}`,
        },
        body: JSON.stringify({ refreshToken }),
      })
      
      if (refreshResponse.ok) {
        const data = await refreshResponse.json()
        if (data.token) {
          const response = NextResponse.next()
          response.cookies.set('auth-token', data.token, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax',
            maxAge: 60 * 60 * 24,
            path: '/',
          })
          response.headers.set('x-authenticated', 'true')
          return response
        }
      }
    } catch (error) {
      const response = NextResponse.next()
      response.cookies.delete('refresh-token')
      
      if (isProtectedPath) {
        if (pathname.startsWith('/api/')) {
          return NextResponse.json(
            { error: 'Authentication required' },
            { status: 401 }
          )
        }
        
        const loginUrl = new URL('/login', request.url)
        loginUrl.searchParams.set('from', pathname)
        return NextResponse.redirect(loginUrl)
      }
      
      return response
    }
  }
  
  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}