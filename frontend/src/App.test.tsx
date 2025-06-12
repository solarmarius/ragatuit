import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from './App';
import '@testing-library/jest-dom';

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    expect(screen.getByText('Vite + React')).toBeInTheDocument();
  });

  it('displays initial count of 0', () => {
    render(<App />);
    expect(screen.getByText('count is 0')).toBeInTheDocument();
  });

  it('increments count when button is clicked', () => {
    render(<App />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    expect(screen.getByText('count is 1')).toBeInTheDocument();
  });

  it('increments count multiple times', () => {
    render(<App />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);
    expect(screen.getByText('count is 3')).toBeInTheDocument();
  });

  it('renders Vite logo with correct attributes', () => {
    render(<App />);
    const viteLogo = screen.getByAltText('Vite logo');
    expect(viteLogo).toBeInTheDocument();
    // Check that src attribute exists and contains SVG data (since Vite transforms it)
    expect(viteLogo).toHaveAttribute('src');
    expect(viteLogo.getAttribute('src')).toContain('svg');
  });

  it('renders React logo with correct attributes', () => {
    render(<App />);
    const reactLogo = screen.getByAltText('React logo');
    expect(reactLogo).toBeInTheDocument();
    expect(reactLogo).toHaveClass('logo', 'react');
  });

  it('renders external links with correct attributes', () => {
    render(<App />);
    const viteLink = screen.getByRole('link', { name: /vite logo/i });
    const reactLink = screen.getByRole('link', { name: /react logo/i });

    expect(viteLink).toHaveAttribute('href', 'https://vite.dev');
    expect(viteLink).toHaveAttribute('target', '_blank');
    expect(viteLink).toHaveAttribute('rel', 'noreferrer');

    expect(reactLink).toHaveAttribute('href', 'https://react.dev');
    expect(reactLink).toHaveAttribute('target', '_blank');
    expect(reactLink).toHaveAttribute('rel', 'noreferrer');
  });

  it('renders HMR instruction text', () => {
    render(<App />);
    // Use getByText with a function matcher to handle text across multiple elements
    expect(
      screen.getByText((content, element) => {
        const hasText =
          element?.textContent === 'Edit src/App.tsx and save to test HMR';
        return hasText;
      })
    ).toBeInTheDocument();
  });

  it('renders learn more instruction', () => {
    render(<App />);
    expect(
      screen.getByText('Click on the Vite and React logos to learn more')
    ).toBeInTheDocument();
  });
});
