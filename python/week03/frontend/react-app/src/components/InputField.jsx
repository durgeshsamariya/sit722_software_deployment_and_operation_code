// /components/InputField.jsx
import React from 'react';

function InputField({ label, id, name, type = 'text', value, onChange, error, ...props }) {
  return (
    <div className="form-group">
      <label htmlFor={id}>{label}:</label>
      {type === 'textarea' ? (
        <textarea
          id={id}
          name={name}
          value={value}
          onChange={onChange}
          className={error ? 'input-error' : ''} // Add class for error styling
          {...props} // Pass through other props like rows, step, etc.
        />
      ) : (
        <input
          type={type}
          id={id}
          name={name}
          value={value}
          onChange={onChange}
          className={error ? 'input-error' : ''} // Add class for error styling
          {...props} // Pass through other props like step
        />
      )}
      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

export default InputField;