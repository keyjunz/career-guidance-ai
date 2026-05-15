import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { register } from '../../services/authApi'

export function RegisterPage() {
  const navigate = useNavigate()
  const [userName, setUserName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [phone, setPhone] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setErrorMessage('')
    setSuccessMessage('')
    setIsSubmitting(true)

    try {
      await register({
        user_name: userName,
        email,
        password,
        phone: phone.trim() || null,
      })
      setSuccessMessage('Account created. Redirecting to login...')
      navigate('/login', { replace: true })
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'Registration failed. Please try again.',
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
            Create account
          </h1>
          <p className="mt-2 text-sm text-on-surface/60">
            Register a client account to start using the chat assistant.
          </p>

          <form className="mt-7 flex flex-col gap-3.5 sm:mt-8 sm:gap-4" onSubmit={handleSubmit}>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-on-surface/75">
              Name
              <input
                className="u-focus rounded-xl border border-outline-variant/18 bg-surface px-4 py-3 text-sm text-on-surface outline-none transition placeholder:text-on-surface/35 focus:border-primary/40"
                minLength={2}
                value={userName}
                onChange={(event) => setUserName(event.target.value)}
                required
              />
            </label>

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
                minLength={6}
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>

            <label className="flex flex-col gap-1.5 text-sm font-medium text-on-surface/75">
              Phone (optional)
              <input
                className="u-focus rounded-xl border border-outline-variant/18 bg-surface px-4 py-3 text-sm text-on-surface outline-none transition placeholder:text-on-surface/35 focus:border-primary/40"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
              />
            </label>

            {errorMessage && (
              <p className="u-alert u-alert-error px-4 py-3 text-sm">{errorMessage}</p>
            )}
            {successMessage && (
              <p className="rounded-xl border border-primary/25 bg-primary/10 px-4 py-3 text-sm text-on-surface">
                {successMessage}
              </p>
            )}

            <button
              className="auth-submit-button u-focus mt-1 rounded-xl px-5 py-3 font-headline text-sm font-semibold text-white transition active:scale-[0.99] disabled:cursor-not-allowed sm:mt-2"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? 'Creating account...' : 'Create account'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-on-surface/55">
            Already registered?{' '}
            <Link
              className="font-semibold text-primary underline-offset-4 hover:underline"
              to="/login"
            >
              Sign in
            </Link>
          </p>
        </div>
      </section>
    </main>
  )
}
