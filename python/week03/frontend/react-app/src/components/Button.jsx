// /components/Button.jsx
import React from 'react';

function Button({ children, onClick, type = 'button', variant = 'primary', disabled = false }) {
  // Determine the correct CSS class based on the variant prop
  const buttonClass = `btn btn-${variant}`;

  return (
    <button
      type={type}
      onClick={onClick}
      className={buttonClass}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export default Button;