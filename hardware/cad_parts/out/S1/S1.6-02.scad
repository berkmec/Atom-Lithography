// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.6-02)
// ============================================================================
// part_id           : S1.6-02
// parent_bom_id     : S1.6
// subsystem         : S1
// part_name         : Kuru-yatakli PH3 gaz yikayici (scrubber) ve 50 ppb gaz dedektoru
// material          : Steel
// temp_stage        : 300 K (tesis)
// vacuum_grade      : Egzoz hatti
// tolerance         : ±10 ppb alarm
// computed_mass_kg  : 118.38646
// envelope_mm       : 440.000 x 440.000 x 1519.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 440.0000;
bbox_y = 440.0000;
bbox_z = 1519.0000;

// Part-specific parametric dimensions
skid_xy = 440.0;
col_od = 340.0;
total_h = 1520.0;
alarm_ppb = 50.0;

// Interface / port parameters (mm)
port_scrubber_inlet_od = 152.000;
port_scrubber_inlet_bore = 144.000;
port_scrubber_exhaust_od = 152.000;
port_scrubber_exhaust_bore = 144.000;

module part_S1_6_02() {
  union() {
    // Welded steel scrubber skid
    translate([0.000, 0.000, -715.000]) cube([440.000, 440.000, 90.000], center=true);
    // Dry-bed catalytic PH3 absorber tower
    translate([-20.000, 0.000, -28.000]) {
      difference() {
        cylinder(d=340.000, h=1280.000, center=true);
        cylinder(d=320.000, h=1282.000, center=true);
      }
    }
    // 50 ppb electrochemical detector & PLC panel
    translate([188.000, 0.000, 220.000]) cube([60.000, 220.000, 320.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-1350.000, 1650.000, 260.000]) rotate([0.000, 0.000, 0.000]) part_S1_6_02();

part_S1_6_02();
