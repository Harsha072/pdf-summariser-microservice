import React from 'react';
import './AboutPage.css';

const AboutPage = () => {
  return (
    <div className="about-page">
      {/* Hero Section */}
      <section className="about-hero">
        <div className="about-hero-content">
          <h1 className="about-title">About Scholar Quest</h1>
          <p className="about-subtitle">
            Empowering researchers and students to navigate the world of academic literature with confidence
          </p>
        </div>
      </section>

      {/* Story Section */}
      <section className="about-section">
        <div className="section-content">
          <h2 className="section-title">Our Story</h2>
          <div className="story-content">
            <p className="story-text">
              Scholar Quest was born from a simple observation: <strong>academic research shouldn't be this hard</strong>.
            </p>
            <p className="story-text">
              As students and researchers ourselves, we experienced firsthand the overwhelming challenge of conducting literature reviews. 
              What should be an exciting journey of discovery often turned into hours of frustration, navigating through 
              countless databases, managing hundreds of papers, and trying to understand how research connects.
            </p>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="about-section problem-section">
        <div className="section-content">
          <h2 className="section-title">The Challenges Students Face</h2>
          <div className="challenges-grid">
            <div className="challenge-card">
              <div className="challenge-icon">
                <i className="fas fa-search"></i>
              </div>
              <h3 className="challenge-title">Information Overload</h3>
              <p className="challenge-description">
                With millions of research papers published annually, finding relevant literature is like searching for a needle in a haystack. 
                Traditional search engines return thousands of results, leaving students overwhelmed and unsure where to start.
              </p>
            </div>

            <div className="challenge-card">
              <div className="challenge-icon">
                <i className="fas fa-clock"></i>
              </div>
              <h3 className="challenge-title">Time-Consuming Process</h3>
              <p className="challenge-description">
                Literature reviews can take weeks or even months. Students spend countless hours manually searching databases, 
                reading abstracts, and trying to identify key papers—time that could be spent on actual research and analysis.
              </p>
            </div>

            <div className="challenge-card">
              <div className="challenge-icon">
                <i className="fas fa-project-diagram"></i>
              </div>
              <h3 className="challenge-title">Missing Connections</h3>
              <p className="challenge-description">
                Understanding how papers relate to each other is crucial but difficult. Without visualization tools, 
                students struggle to see the bigger picture—which papers are foundational, which are emerging, and how research has evolved.
              </p>
            </div>

            <div className="challenge-card">
              <div className="challenge-icon">
                <i className="fas fa-graduation-cap"></i>
              </div>
              <h3 className="challenge-title">Steep Learning Curve</h3>
              <p className="challenge-description">
                New researchers lack experience in efficient literature search strategies. Learning to use multiple academic 
                databases, understanding search syntax, and evaluating paper quality adds another layer of complexity.
              </p>
            </div>

            <div className="challenge-card">
              <div className="challenge-icon">
                <i className="fas fa-dollar-sign"></i>
              </div>
              <h3 className="challenge-title">Cost Barriers</h3>
              <p className="challenge-description">
                Many academic databases require expensive subscriptions. Students without institutional access 
                struggle to find and access the papers they need, limiting their research capabilities.
              </p>
            </div>

            <div className="challenge-card">
              <div className="challenge-icon">
                <i className="fas fa-folder-open"></i>
              </div>
              <h3 className="challenge-title">Poor Organization</h3>
              <p className="challenge-description">
                Managing research papers across different folders, bookmarks, and notes becomes chaotic. 
                Students lose track of important papers and waste time re-finding sources they've already discovered.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section className="about-section solution-section">
        <div className="section-content">
          <h2 className="section-title">How Scholar Quest Helps</h2>
          <p className="section-intro">
            We built Scholar Quest to address these challenges with AI-powered intelligence and intuitive visualization
          </p>

          <div className="solutions-list">
            <div className="solution-item">
              <div className="solution-number">1</div>
              <div className="solution-content">
                <h3 className="solution-title">AI-Powered Paper Discovery</h3>
                <p className="solution-description">
                  Our intelligent search engine understands your research questions in natural language. Instead of keyword matching, 
                  we use advanced AI to find papers that are truly relevant to your topic, saving hours of manual searching.
                </p>
                <ul className="solution-features">
                  <li>Natural language search - ask questions like you would to a colleague</li>
                  <li>Semantic understanding - finds papers even when they use different terminology</li>
                  <li>Ranked results - most relevant papers appear first</li>
                </ul>
              </div>
            </div>

            <div className="solution-item">
              <div className="solution-number">2</div>
              <div className="solution-content">
                <h3 className="solution-title">Interactive Citation Graphs</h3>
                <p className="solution-description">
                  See the research landscape at a glance with beautiful, interactive visualizations. Our citation graphs 
                  show you which papers are foundational, which build upon them, and how ideas have evolved over time.
                </p>
                <ul className="solution-features">
                  <li>Visual network maps showing paper relationships</li>
                  <li>Identify seminal works and emerging research</li>
                  <li>Understand research evolution with timeline views</li>
                </ul>
              </div>
            </div>

            <div className="solution-item">
              <div className="solution-number">3</div>
              <div className="solution-content">
                <h3 className="solution-title">Unified Research Hub</h3>
                <p className="solution-description">
                  Keep all your research organized in one place. Save papers, track your search history, and build 
                  your personal research library—all accessible from anywhere.
                </p>
                <ul className="solution-features">
                  <li>Save and bookmark important papers</li>
                  <li>Track search history to revisit past research</li>
                  <li>Access your research from any device</li>
                </ul>
              </div>
            </div>

            <div className="solution-item">
              <div className="solution-number">4</div>
              <div className="solution-content">
                <h3 className="solution-title">Free and Open Access</h3>
                <p className="solution-description">
                  We believe research should be accessible to everyone. Scholar Quest is free to use and connects 
                  to open-access databases, removing cost barriers for students worldwide.
                </p>
                <ul className="solution-features">
                  <li>Completely free - no subscriptions or hidden fees</li>
                  <li>Access to millions of open-access papers</li>
                  <li>No institutional access required</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Impact Section */}
      <section className="about-section impact-section">
        <div className="section-content">
          <h2 className="section-title">Our Impact</h2>
          <div className="impact-stats">
            <div className="stat-card">
              <div className="stat-number">10x</div>
              <div className="stat-label">Faster Literature Reviews</div>
              <p className="stat-description">
                Students complete literature reviews in days instead of weeks
              </p>
            </div>
            <div className="stat-card">
              <div className="stat-number">Millions</div>
              <div className="stat-label">Papers Accessible</div>
              <p className="stat-description">
                Access to comprehensive open-access research databases
              </p>
            </div>
            <div className="stat-card">
              <div className="stat-number">150+</div>
              <div className="stat-label">Countries Reached</div>
              <p className="stat-description">
                Helping students and researchers worldwide
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Mission Section */}
      <section className="about-section mission-section">
        <div className="section-content">
          <h2 className="section-title">Our Mission</h2>
          <div className="mission-content">
            <p className="mission-text">
              Our mission is to <strong>democratize academic research</strong> by making literature discovery 
              fast, intuitive, and accessible to everyone. We believe that:
            </p>
            <ul className="mission-list">
              <li>
                <i className="fas fa-check-circle"></i>
                <span>Every student deserves powerful research tools, regardless of their institution or budget</span>
              </li>
              <li>
                <i className="fas fa-check-circle"></i>
                <span>Technology should simplify research, not complicate it</span>
              </li>
              <li>
                <i className="fas fa-check-circle"></i>
                <span>Understanding research connections is as important as finding individual papers</span>
              </li>
              <li>
                <i className="fas fa-check-circle"></i>
                <span>AI can augment human intelligence to accelerate discovery</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="about-cta-section">
        <div className="cta-content">
          <h2 className="cta-title">Ready to Transform Your Research?</h2>
          <p className="cta-description">
            Join thousands of students and researchers who are discovering papers faster and understanding research better.
          </p>
          <button 
            className="cta-button"
            onClick={() => window.location.href = '/search'}
          >
            Start Exploring
            <i className="fas fa-arrow-right"></i>
          </button>
        </div>
      </section>
    </div>
  );
};

export default AboutPage;
