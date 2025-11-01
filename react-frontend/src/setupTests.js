import '@testing-library/jest-dom';

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  observe() {
    return null;
  }
  disconnect() {
    return null;  
  }
  unobserve() {
    return null;
  }
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  observe() {
    return null;
  }
  disconnect() {
    return null;
  }
  unobserve() {
    return null;
  }
};

// Mock PDF.js worker
global.pdfjsLib = {
  GlobalWorkerOptions: {
    workerSrc: '/pdf.worker.js'
  },
  getDocument: jest.fn(() => Promise.resolve({
    numPages: 1,
    getPage: jest.fn(() => Promise.resolve({
      getViewport: jest.fn(() => ({ width: 800, height: 1000 })),
      render: jest.fn(() => ({ promise: Promise.resolve() })),
      getTextContent: jest.fn(() => Promise.resolve({ items: [] }))
    }))
  }))
};

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock scrollIntoView
Element.prototype.scrollIntoView = jest.fn();

// Mock URL.createObjectURL
global.URL.createObjectURL = jest.fn(() => 'mocked-url');
global.URL.revokeObjectURL = jest.fn();