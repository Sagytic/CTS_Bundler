import React from 'react';

export default function Spinner({
  size = 20,
  borderWidth = 3,
  borderColor = '#444',
  borderTopColor = 'var(--accent-color)',
  style = {}
}) {
  return (
    <div
      className="spinner"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        borderWidth: `${borderWidth}px`,
        borderColor: borderColor,
        borderTopColor: borderTopColor,
        ...style
      }}
    />
  );
}
