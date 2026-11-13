import React, { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import {
  KeyRound,
  Lock,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import ForgotHeader from './components/ForgotHeader';
import ForgotStepEmail from './components/ForgotStepEmail';
import ForgotStepOtp from './components/ForgotStepOtp';
import ForgotStepReset from './components/ForgotStepReset';

export default function ForgotPasswordPage({ onGoLogin, prefilledEmail = '' }) {
  const { forgotPassword, verifyOtp, resetPassword } = useAuth();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState(prefilledEmail);
  const [otpCode, setOtpCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Countdown timer for 10 minutes
  const [timeLeft, setTimeLeft] = useState(600);
  const [timerActive, setTimerActive] = useState(false);

  useEffect(() => {
    if (prefilledEmail) {
      setEmail(prefilledEmail);
    }
  }, [prefilledEmail]);

  useEffect(() => {
    let interval = null;
    if (timerActive && timeLeft > 0) {
      interval = setInterval(() => setTimeLeft((prev) => prev - 1), 1000);
    } else if (timeLeft <= 0) {
      setTimerActive(false);
    }
    return () => clearInterval(interval);
  }, [timerActive, timeLeft]);

  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Password rules validation
  const hasLen = password.length >= 8;
  const hasLetter = /[a-zA-Z]/.test(password);
  const hasDigit = /\d/.test(password);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/`~]/.test(password);
  const pwdScore = [hasLen, hasLetter, hasDigit, hasSpecial].filter(Boolean).length;
  const isPwdValid = pwdScore === 4;
  const isMatch = confirmPassword.length > 0 && password === confirmPassword;

  // Step 1: Send OTP to Email
  const handleRequestOtp = async (e) => {
    if (e) e.preventDefault();
    const targetEmail = email.trim().toLowerCase();
    if (!targetEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(targetEmail)) {
      setError('Please enter a valid work email address.');
      return;
    }

    setBusy(true);
    setError('');
    setSuccess('');
    try {
      await forgotPassword(targetEmail);
      setStep(2);
      setTimeLeft(600);
      setTimerActive(true);
      setOtpCode('');
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to send verification code. Please check your email and try again.';
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  // Step 2: Verify OTP Only (Transition to Step 3)
  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    const cleanOtp = otpCode.trim();
    if (cleanOtp.length !== 6 || !/^\d+$/.test(cleanOtp)) {
      setError('Please enter a valid 6-digit verification code.');
      return;
    }

    setBusy(true);
    setError('');
    try {
      await verifyOtp({
        email: email.trim().toLowerCase(),
        otp_code: cleanOtp,
      });

      setStep(3);
      setError('');
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Incorrect or expired verification code. Please try again.';
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  // Step 3: Set New Password
  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!isPwdValid) {
      setError('Password must meet all 4 security criteria.');
      return;
    }
    if (password !== confirmPassword) {
      setError('New password and confirm password do not match.');
      return;
    }

    setBusy(true);
    setError('');
    try {
      await resetPassword({
        email: email.trim().toLowerCase(),
        otp_code: otpCode.trim(),
        new_password: password,
      });

      setSuccess('Your password has been reset successfully! Redirecting to Sign In...');
      setTimeout(() => {
        onGoLogin(email.trim().toLowerCase());
      }, 1500);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to reset password. Please try again.';
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  const strengthColors = ['#e4e4e7', '#ef4444', '#f59e0b', '#3b82f6', '#10b981'];
  const strengthLabels = ['Empty', 'Weak', 'Moderate', 'Strong', 'Secure'];

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#fafafa',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem 1.5rem',
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    }}>
      <div style={{
        width: '100%',
        maxWidth: '440px',
        backgroundColor: '#ffffff',
        border: '1px solid #e4e4e7',
        borderRadius: '10px',
        padding: '2.25rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
        boxShadow: '0 4px 16px rgba(0,0,0,0.03)',
      }}>
        <ForgotHeader step={step} email={email} />

        {/* Error Alert */}
        {error && (
          <div style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fee2e2',
            borderRadius: '8px',
            padding: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: '#991b1b',
            fontSize: '0.8125rem',
          }}>
            <AlertCircle size={16} strokeWidth={1.75} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Success Alert */}
        {success && (
          <div style={{
            backgroundColor: '#ecfdf5',
            border: '1px solid #d1fae5',
            borderRadius: '8px',
            padding: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: '#065f46',
            fontSize: '0.8125rem',
          }}>
            <CheckCircle2 size={16} strokeWidth={1.75} style={{ flexShrink: 0 }} />
            <span>{success}</span>
          </div>
        )}

        {/* STEP 1 */}
        {step === 1 && (
          <ForgotStepEmail
            email={email}
            setEmail={setEmail}
            setError={setError}
            busy={busy}
            onGoLogin={onGoLogin}
            handleRequestOtp={handleRequestOtp}
          />
        )}

        {/* STEP 2 */}
        {step === 2 && (
          <ForgotStepOtp
            email={email}
            setStep={setStep}
            setError={setError}
            otpCode={otpCode}
            setOtpCode={setOtpCode}
            timeLeft={timeLeft}
            formatTimer={formatTimer}
            busy={busy}
            handleVerifyOtp={handleVerifyOtp}
            handleRequestOtp={handleRequestOtp}
          />
        )}

        {/* STEP 3 */}
        {step === 3 && (
          <ForgotStepReset
            email={email}
            password={password}
            setPassword={setPassword}
            confirmPassword={confirmPassword}
            setConfirmPassword={setConfirmPassword}
            showPwd={showPwd}
            setShowPwd={setShowPwd}
            showConfirm={showConfirm}
            setShowConfirm={setShowConfirm}
            setError={setError}
            busy={busy}
            pwdScore={pwdScore}
            strengthColors={strengthColors}
            strengthLabels={strengthLabels}
            hasLen={hasLen}
            hasLetter={hasLetter}
            hasDigit={hasDigit}
            hasSpecial={hasSpecial}
            isPwdValid={isPwdValid}
            isMatch={isMatch}
            handleResetPassword={handleResetPassword}
          />
        )}

        {/* Security Policy Footer */}
        <div style={{ borderTop: '1px solid #e4e4e7', paddingTop: '1rem', textAlign: 'center' }}>
          <p style={{ fontSize: '0.75rem', color: '#a1a1aa' }}>
            Protected by CockroachDB &bull; Bcrypt Password Hashing &bull; Session Invalidation
          </p>
        </div>
      </div>
    </div>
  );
}
