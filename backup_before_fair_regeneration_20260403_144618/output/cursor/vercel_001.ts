import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { jwtVerify } from 'jose'

const AUTH_COOKIE = 'auth_token'

const JWT_ALG = 'HS256'

const publicMatchers: RegExp[] = [
  /^\/$/,
  /^\/login$/,
  /^\/register$/,
  /^\/api\/auth\/(login|register|logout|callback)$/,
  /^\/_next\//,
  /^\/favicon\.ico$/,
]

function getJwtSecretKey(): Uint8Array | null {
  const raw = process.env.JWT_SECRET
  if (!raw) return null
  return new TextEncoder().encode(raw)
}

function isPublicPath(pathname: string): boolean {
  return publicMatchers.some((re) => re.test(pathname))
}

function isAuthOnlyPath(pathname: string): boolean {
  return pathname === '/login' || pathname === '/register'
}

async function validateToken(token: string): Promise<boolean> {
  const secret = getJwtSecretKey()
  if (!secret) return false
  try {
    const { payload } = await jwtVerify(token, secret, { algorithms: [JWT_ALG] })
    if (typeof payload.exp === 'number' && Date.now() >= payload.exp * 1000) {
      return false
    }
    return Boolean(payload.sub)
  } catch {
    return false
  }
}

function jsonUnauthorized(): NextResponse {
  return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
}

function redirectToLogin(request: NextRequest, pathname: string): NextResponse {
  const url = request.nextUrl.clone()
  url.pathname = '/login'
  url.searchParams.set('from', pathname)
  const res = NextResponse.redirect(url)
  res.cookies.delete(AUTH_COOKIE)
  return res
}

export async function middleware(request: NextRequest): Promise<NextResponse> {
  const { pathname } = request.nextUrl
  const token = request.cookies.get(AUTH_COOKIE)?.value ?? null
  const authenticated = token ? await validateToken(token) : false

  if (isPublicPath(pathname)) {
    if (authenticated && isAuthOnlyPath(pathname)) {
      const url = request.nextUrl.clone()
      url.pathname = '/'
      url.searchParams.delete('from')
      return NextResponse.redirect(url)
    }
    return NextResponse.next()
  }

  if (!authenticated) {
    if (pathname.startsWith('/api/')) {
      return jsonUnauthorized()
    }
    return redirectToLogin(request, pathname)
  }

  const headers = new Headers(request.headers)
  if (token) {
    headers.set('x-auth-present', 'true')
  }

  return NextResponse.next({ request: { headers } })
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|.*\\..*).*)'],
}