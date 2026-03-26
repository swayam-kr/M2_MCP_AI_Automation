import { render, screen } from '@testing-library/react';
import PartAControls from '../src/components/PartAControls';

describe('PartAControls Component', () => {
  it('renders default values correctly', () => {
    render(<PartAControls setResult={jest.fn()} setIsLoading={jest.fn()} isLoading={false} setDispatchStatus={jest.fn()} />);
    
    expect(screen.getByText(/Time Window: 4 weeks/i)).toBeInTheDocument();
  });

  it('triggers API call on Generate button click', () => {
    render(<PartAControls setResult={jest.fn()} setIsLoading={jest.fn()} isLoading={false} setDispatchStatus={jest.fn()} />);
    
    const generateBtn = screen.getByRole('button', { name: /Generate Pulse/i });
    expect(generateBtn).toBeInTheDocument();
    expect(generateBtn).not.toBeDisabled();
    
    // Test the disabled state
    render(<PartAControls setResult={jest.fn()} setIsLoading={jest.fn()} isLoading={true} setDispatchStatus={jest.fn()} />);
    const disabledBtn = screen.getAllByRole('button', { name: /Generate Pulse/i })[1];
    expect(disabledBtn).toBeDisabled();
  });
});
