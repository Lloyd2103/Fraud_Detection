import React from 'react';

export function RequireRole({ user, allowedRoles = [], children }) {
  if (!user) return null;

  const userRole = (user.role || '').toLowerCase();
  const hasAccess = allowedRoles.map((r) => r.toLowerCase()).includes(userRole);

  if (!hasAccess) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-6">
        <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-gray-800 mb-2">403 — Access denied</h2>
        <p className="text-sm text-gray-500 max-w-md">
          Your account role ({user.role}) is not allowed to use this feature.
        </p>
      </div>
    );
  }

  return children;
}

export default RequireRole;

