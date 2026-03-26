import { render, screen, fireEvent } from '@testing-library/react';
import PartCGates from '../src/components/PartCGates';

describe('PartCGates Component', () => {
  const defaultProps = {
    activeContent: { status: 'success' },
    contentType: 'pulse',
    setIsLoading: jest.fn(),
    isLoading: false,
    setDispatchStatus: jest.fn(),
  };

  it('renders dispatch buttons correctly', () => {
    render(<PartCGates {...defaultProps} />);
    
    expect(screen.getByText(/1. Append to Google Doc/i)).toBeInTheDocument();
    expect(screen.getByText(/2. Generate Email Draft/i)).toBeInTheDocument();
    expect(screen.getByText(/3. Generate & Auto-Send Email/i)).toBeInTheDocument();
  });

  it('disables buttons when isLoading is true', () => {
    render(<PartCGates {...defaultProps} isLoading={true} />);
    
    const appendBtn = screen.getByRole('button', { name: /1. Append to Google Doc/i });
    const draftBtn = screen.getByRole('button', { name: /2. Generate Email Draft/i });
    const autoSendBtn = screen.getByRole('button', { name: /3. Generate & Auto-Send Email/i });

    expect(appendBtn).toBeDisabled();
    expect(draftBtn).toBeDisabled();
    expect(autoSendBtn).toBeDisabled();
  });

  it('disables auto-send button when recipients are empty', () => {
    render(<PartCGates {...defaultProps} />);
    
    const autoSendBtn = screen.getByRole('button', { name: /3. Generate & Auto-Send Email/i });
    expect(autoSendBtn).toBeDisabled();
  });

  it('enables auto-send button when recipients are provided', () => {
    render(<PartCGates {...defaultProps} />);
    
    const recipientsInput = screen.getByPlaceholderText(/ceo@groww.in/i);
    fireEvent.change(recipientsInput, { target: { value: 'test@example.com' } });
    
    const autoSendBtn = screen.getByRole('button', { name: /3. Generate & Auto-Send Email/i });
    expect(autoSendBtn).not.toBeDisabled();
  });
});
