import React from "react";
import leftHandImg from "../assets/hand-left.png";
import rightHandImg from "../assets/hand-right.png";

export function HandsControl({ activeHand = "both", onChange }) {
  return (
    <div className="bottom-group hands-group">
      <div className="hands-toggle-row" role="group" aria-label="Hands filter">
        <span className="hands-title-inline">Hands</span>
        <button
          type="button"
          className={`hand-image-button ${activeHand === "left" ? "is-active" : ""}`}
          onClick={() => onChange?.("left")}
          aria-pressed={activeHand === "left"}
        >
          <img src={leftHandImg} alt="Left hand" className="hand-button-image" />
          <span className="hand-button-label left">Left</span>
        </button>

        <button
          type="button"
          className={`hand-image-button ${activeHand === "both" ? "is-active" : ""}`}
          onClick={() => onChange?.("both")}
          aria-pressed={activeHand === "both"}
        >
          <div className="both-hands-preview">
            <img src={leftHandImg} alt="" className="hand-button-image both-small" />
            <img src={rightHandImg} alt="" className="hand-button-image both-small" />
          </div>
          <span className="hand-button-label both">Both</span>
        </button>

        <button
          type="button"
          className={`hand-image-button ${activeHand === "right" ? "is-active" : ""}`}
          onClick={() => onChange?.("right")}
          aria-pressed={activeHand === "right"}
        >
          <img src={rightHandImg} alt="Right hand" className="hand-button-image" />
          <span className="hand-button-label right">Right</span>
        </button>
      </div>
    </div>
  );
}

export default HandsControl;