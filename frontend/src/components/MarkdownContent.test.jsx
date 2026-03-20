import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MarkdownContent from './MarkdownContent'

describe('MarkdownContent', () => {
  it('renders plain text', () => {
    render(<MarkdownContent content="Hello world" />)
    expect(screen.getByText('Hello world')).toBeInTheDocument()
  })

  it('renders markdown headings', () => {
    render(<MarkdownContent content="# Title" />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Title')
  })

  it('applies optional className', () => {
    const { container } = render(<MarkdownContent content="x" className="custom" />)
    const wrapper = container.querySelector('.markdown-github-theme.custom')
    expect(wrapper).toBeInTheDocument()
  })
})
