import { Component } from "react";

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("Unhandled error in the UI:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="state-message error" style={{ padding: "2rem", textAlign: "center" }}>
          <p>Something went wrong. Try refreshing the page.</p>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;