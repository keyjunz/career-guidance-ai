import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { login } from '../../services/authApi'

export function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('admin@system.local')
  const [password, setPassword] = useState('admin123')
  const [errorMessage, setErrorMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setErrorMessage('')
    setIsSubmitting(true)

    try {
      await login({ email, password })
      navigate('/chat', { replace: true })
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'Login failed. Please try again.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen bg-background text-on-surface kv-texture-overlay">
      <section className="relative z-10 grid min-h-screen place-items-center px-4 py-10 sm:px-6">
        <div className="u-card w-full max-w-md rounded-2xl p-7 sm:p-8">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.28em] text-primary/90">
            Career Guidance AI
          </p>
          <h1 className="font-headline text-2xl font-semibold tracking-tight sm:text-3xl">
            Welcome back
          </h1>
          <p className="mt-2 text-sm text-on-surface/60">
            Sign in to continue your career guidance chat session.
          </p>

          <form className="mt-7 flex flex-col gap-3.5 sm:mt-8 sm:gap-4" onSubmit={handleSubmit}>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-on-surface/75">
              Email
              <input
                className="u-focus rounded-xl border border-outline-variant/18 bg-surface px-4 py-3 text-sm text-on-surface outline-none transition placeholder:text-on-surface/35 focus:border-primary/40"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>

            <label className="flex flex-col gap-1.5 text-sm font-medium text-on-surface/75">
              Password
              <input
                className="u-focus rounded-xl border border-outline-variant/18 bg-surface px-4 py-3 text-sm text-on-surface outline-none transition placeholder:text-on-surface/35 focus:border-primary/40"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>

            {errorMessage && (
              <p className="rounded-xl border border-red-400/25 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {errorMessage}
              </p>
            )}

            <button
              className="auth-submit-button u-focus mt-1 rounded-xl px-5 py-3 font-headline text-sm font-semibold text-white transition active:scale-[0.99] disabled:cursor-not-allowed sm:mt-2"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-on-surface/55">
            Need an account?{' '}
            <Link
              className="font-semibold text-primary underline-offset-4 hover:underline"
              to="/register"
            >
              Create one
            </Link>
          </p>
        </div>
      </section>
    </main>
  )
}
