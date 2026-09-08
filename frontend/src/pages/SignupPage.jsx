import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth.jsx'

export default function SignupPage() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await signup(email, password)
      navigate('/import')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-24 px-6">
      <h1 className="text-xl font-semibold text-slate-100 mb-1">Sign up</h1>
      <p className="text-sm text-slate-500 mb-6">
        Your imported hands are private to your account only.
      </p>

      <form onSubmit={onSubmit} className="flex flex-col gap-4 rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-6">
        <Field label="Email">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-100"
          />
        </Field>
        <Field label="Password" hint="At least 8 characters">
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-100"
          />
        </Field>

        {error && <p className="text-sm text-rose-400">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="mt-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-sm font-medium py-2"
        >
          {submitting ? 'Creating account…' : 'Sign up'}
        </button>
      </form>

      <p className="text-sm text-slate-500 mt-4 text-center">
        Already have an account?{' '}
        <Link to="/login" className="text-cyan-400 hover:underline">
          Log in
        </Link>
      </p>
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label} {hint && <span className="normal-case text-slate-600">— {hint}</span>}
      </span>
      {children}
    </label>
  )
}
