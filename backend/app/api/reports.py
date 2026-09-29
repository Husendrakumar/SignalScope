from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, Any, Optional
from fpdf import FPDF
import io

router = APIRouter(prefix="/api/reports", tags=["Reports"])

class ReportRequest(BaseModel):
    signal_id: str
    filename: str
    format: str
    data_type: str
    sample_rate: int
    sample_count: int
    duration_seconds: float
    analysis_data: Optional[Dict[str, Any]] = None
    modulation_data: Optional[Dict[str, Any]] = None
    pipeline_status: Optional[Dict[str, Any]] = None

@router.post("/generate")
async def generate_report(req: ReportRequest):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "SIGNALSCOPE", ln=True, align="C")
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Automatic Radio Signal Analysis Report", ln=True, align="C")
        pdf.line(10, 30, 200, 30)
        pdf.ln(10)
        
        def add_section(title):
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 8, title, ln=True)
            pdf.set_font("Helvetica", "", 10)

        def add_row(label, value):
            pdf.cell(60, 6, label + ":")
            pdf.cell(0, 6, str(value), ln=True)

        # 1. SIGNAL INFORMATION
        add_section("1. SIGNAL INFORMATION")
        add_row("File name", req.filename)
        add_row("File format", req.format)
        add_row("Data type", req.data_type)
        add_row("Sample rate", f"{req.sample_rate} Hz")
        add_row("Sample count", str(req.sample_count))
        add_row("Signal duration", f"{req.duration_seconds} seconds")

        # 2. SIGNAL STATISTICS
        stats = req.analysis_data.get("statistics", {}) if req.analysis_data else {}
        if stats:
            add_section("2. SIGNAL STATISTICS")
            add_row("RMS amplitude", round(stats.get("rms", 0), 4))
            add_row("Peak value", round(stats.get("peak", 0), 4))
            add_row("Peak-to-peak", round(stats.get("peak_to_peak", 0), 4))
            add_row("Average power", round(stats.get("average_power", 0), 4))

        # 3. FREQUENCY & BANDWIDTH
        freq = req.analysis_data.get("frequency", {}) if req.analysis_data else {}
        bw = req.analysis_data.get("bandwidth", {}) if req.analysis_data else {}
        if freq or bw:
            add_section("3. FREQUENCY & BANDWIDTH")
            add_row("Dominant frequency", f"{freq.get('dominant_frequency_khz', 0)} kHz")
            add_row("Peak spectrum power", f"{freq.get('peak_magnitude_db', 0)} dB")
            add_row("Occupied bandwidth", f"{round(bw.get('bandwidth_hz', 0)/1000.0, 2)} kHz")
            add_row("Bandwidth lower bound", f"{round(bw.get('lower_frequency_hz', 0)/1000.0, 2)} kHz")
            add_row("Bandwidth upper bound", f"{round(bw.get('upper_frequency_hz', 0)/1000.0, 2)} kHz")

        # 4. NOISE & SIGNAL QUALITY
        noise = req.analysis_data.get("noise", {}) if req.analysis_data else {}
        if noise:
            add_section("4. NOISE & SIGNAL QUALITY")
            add_row("Estimated SNR", f"{noise.get('estimated_snr_db', 0)} dB")
            add_row("Estimated signal power", round(noise.get("estimated_signal_power", 0), 4))
            add_row("Estimated noise power", round(noise.get("estimated_noise_power", 0), 4))
            add_row("Estimation method", noise.get("method", "N/A"))

        # 5. SIGNAL PRESENCE
        act = req.analysis_data.get("activity", {}) if req.analysis_data else {}
        if act:
            add_section("5. SIGNAL PRESENCE")
            add_row("Signal status", act.get("status", "N/A"))
            add_row("Activity ratio", act.get("activity_ratio", 0))
            add_row("Active time interval", f"{act.get('active_start_time', 0)}s - {act.get('active_end_time', 0)}s")

        # 6. MODULATION RECOGNITION
        mod = req.modulation_data if req.modulation_data else {}
        if mod:
            add_section("6. MODULATION RECOGNITION")
            add_row("Modulation type", mod.get("modulation", "UNKNOWN"))
            add_row("Confidence score", f"{mod.get('confidence', 0)*100}%")
            evidence = mod.get("evidence", [])
            if evidence:
                pdf.cell(60, 6, "Classification evidence:")
                pdf.ln(6)
                for e in evidence:
                    pdf.cell(5, 6, "-")
                    pdf.multi_cell(0, 6, str(e))
            else:
                add_row("Classification evidence", "None")

        # 7. DECODING / PIPELINE STATUS
        ps = req.pipeline_status if req.pipeline_status else {}
        if ps:
            add_section("7. DECODING / PIPELINE STATUS")
            for stage, status in ps.items():
                add_row(stage, status)

        # 8. FINAL RESULT
        add_section("8. FINAL RESULT")
        dom_freq = freq.get('dominant_frequency_khz', 0) if freq else 0
        snr_val = noise.get('estimated_snr_db', 0) if noise else 0
        mod_type = mod.get("modulation", "UNKNOWN") if mod else "UNKNOWN"
        summary = f"Detected dominant frequency: {dom_freq} kHz.\nEstimated SNR: {snr_val} dB.\nModulation classification: {mod_type}."
        pdf.multi_cell(0, 6, summary)

        pdf.ln(15)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "Generated by SignalScope", align="C")

        # Output PDF
        pdf_bytes = pdf.output(dest='S')
        
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=SignalScope_Report_{req.filename}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
