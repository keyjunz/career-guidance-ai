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
    <main className="min-h-screen bg-surface text-on-surface kv-texture-overlay">
      <section className="relative z-10 grid min-h-screen place-items-center px-6">
        <div className="w-full max-w-md rounded-3xl border border-outline-variant/15 bg-surface-container-high/80 p-8 shadow-[0_30px_100px_rgba(0,0,0,0.45)] backdrop-blur">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.35em] text-primary">
            Career Guidance AI
          </p>
          <h1 className="font-headline text-3xl font-extrabold tracking-tight">
            Create account
          </h1>
          <p className="mt-2 text-sm text-on-surface/65">
            Register a client account to start using the chat assistant.
          </p>

          <form className="mt-8 flex flex-col gap-4" onSubmit={handleSubmit}>
            <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface/80">
              Name
              <input
                className="rounded-2xl border border-outline-variant/20 bg-surface px-4 py-3 text-on-surface outline-none transition focus:border-primary"
                minLength={2}
                value={userName}
                onChange={(event) => setUserName(event.target.value)}
                required
              />
            </label>

            <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface/80">
              Email
              <input
                className="rounded-2xl border border-outline-variant/20 bg-surface px-4 py-3 text-on-surface outline-none transition focus:border-primary"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>

            <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface/80">
              Password
              <input
                className="rounded-2xl border border-outline-variant/20 bg-surface px-4 py-3 text-on-surface outline-none transition focus:border-primary"
                minLength={6}
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>

            <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface/80">
              Phone (optional)
              <input
                className="rounded-2xl border border-outline-variant/20 bg-surface px-4 py-3 text-on-surface outline-none transition focus:border-primary"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
              />
            </label>

            {errorMessage && (
              <p className="rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {errorMessage}
              </p>
            )}
            {successMessage && (
              <p className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                {successMessage}
              </p>
            )}

            <button
              className="auth-submit-button mt-2 rounded-2xl px-5 py-3 font-headline text-sm font-bold text-white transition active:scale-[0.98] disabled:cursor-not-allowed"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? 'Creating account...' : 'Create account'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-on-surface/60">
            Already registered?{' '}
            <Link className="font-semibold text-primary hover:text-sky-300" to="/login">
              Sign in
            </Link>
          </p>
        </div>
      </section>
    </main>
  )
}
