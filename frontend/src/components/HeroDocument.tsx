import './HeroDocument.css';

/**
 * Decorative 3D form for the landing hero — glossy white paper with indigo
 * edges tied to the global theme tokens in index.css.
 */
export default function HeroDocument() {
  return (
    <div className="hero-doc" aria-hidden>
      <div className="hero-doc__glow" />
      <div className="hero-doc__scene">
        <div className="hero-doc__motion">
          <div className="hero-doc__shadow" />
          <div className="hero-doc__rig">
            <div className="hero-doc__sheet">
              <div className="hero-doc__face hero-doc__face--front">
                <div className="hero-doc__water-border" aria-hidden>
                  <svg viewBox="0 0 100 138" preserveAspectRatio="none">
                    <rect
                      className="hero-doc__border-travel"
                      x="0"
                      y="0"
                      width="100"
                      height="138"
                      pathLength="100"
                    />
                  </svg>
                </div>
                <div className="hero-doc__inner">
                <div className="hero-doc__sheen" />
                <div className="hero-doc__form">
                  <header className="hero-doc__form-header">
                    <p className="hero-doc__form-ref">Ref. GOV-2026-0412</p>
                    <h2 className="hero-doc__form-title">Official Notice</h2>
                    <div className="hero-doc__form-rule" />
                  </header>

                  <p className="hero-doc__section">Applicant details</p>
                  <div className="hero-doc__field">
                    <span className="hero-doc__label">Full name</span>
                    <div className="hero-doc__input" />
                  </div>
                  <div className="hero-doc__field-row">
                    <div className="hero-doc__field">
                      <span className="hero-doc__label">Date of birth</span>
                      <div className="hero-doc__input" />
                    </div>
                    <div className="hero-doc__field">
                      <span className="hero-doc__label">PPS number</span>
                      <div className="hero-doc__input" />
                    </div>
                  </div>
                  <div className="hero-doc__field">
                    <span className="hero-doc__label">Correspondence address</span>
                    <div className="hero-doc__input" />
                    <div className="hero-doc__input" />
                  </div>
                  <div className="hero-doc__field-row hero-doc__field-row--3">
                    <div className="hero-doc__field">
                      <span className="hero-doc__label">City</span>
                      <div className="hero-doc__input" />
                    </div>
                    <div className="hero-doc__field">
                      <span className="hero-doc__label">County</span>
                      <div className="hero-doc__input" />
                    </div>
                    <div className="hero-doc__field">
                      <span className="hero-doc__label">Eircode</span>
                      <div className="hero-doc__input" />
                    </div>
                  </div>

                  <p className="hero-doc__section">Property &amp; tenancy</p>
                  <div className="hero-doc__field">
                    <span className="hero-doc__label">Rented dwelling address</span>
                    <div className="hero-doc__input" />
                  </div>
                  <div className="hero-doc__field-row">
                    <div className="hero-doc__field">
                      <span className="hero-doc__label">Tenancy commenced</span>
                      <div className="hero-doc__input" />
                    </div>
                    <div className="hero-doc__field">
                      <span className="hero-doc__label">RTB registration no.</span>
                      <div className="hero-doc__input" />
                    </div>
                  </div>
                  <div className="hero-doc__field-row">
                    <div className="hero-doc__field">
                      <span className="hero-doc__label">Monthly rent</span>
                      <div className="hero-doc__input" />
                    </div>
                    <div className="hero-doc__field">
                      <span className="hero-doc__label">Deposit held</span>
                      <div className="hero-doc__input" />
                    </div>
                  </div>

                  <p className="hero-doc__section">Declaration</p>
                  <div className="hero-doc__checkbox">
                    <span className="hero-doc__checkbox-box" />
                    <span className="hero-doc__checkbox-label">
                      I acknowledge receipt of this notice
                    </span>
                  </div>
                  <div className="hero-doc__checkbox">
                    <span className="hero-doc__checkbox-box" />
                    <span className="hero-doc__checkbox-label">
                      I have been advised of my statutory rights
                    </span>
                  </div>

                  <div className="hero-doc__field-row hero-doc__sig-row">
                    <div className="hero-doc__signature">
                      <span className="hero-doc__label">Signature</span>
                      <div className="hero-doc__sig-line" />
                    </div>
                    <div className="hero-doc__signature">
                      <span className="hero-doc__label">Date</span>
                      <div className="hero-doc__sig-line" />
                    </div>
                  </div>
                </div>
                </div>
              </div>

              <div className="hero-doc__face hero-doc__face--back" />
              <div className="hero-doc__face hero-doc__face--right" />
              <div className="hero-doc__face hero-doc__face--left" />
              <div className="hero-doc__face hero-doc__face--top" />
              <div className="hero-doc__face hero-doc__face--bottom" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
