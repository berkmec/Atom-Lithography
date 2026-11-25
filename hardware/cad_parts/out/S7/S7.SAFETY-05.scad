// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.SAFETY-05)
// ============================================================================
// part_id           : S7.SAFETY-05
// parent_bom_id     : S7.SAFETY
// subsystem         : S7
// part_name         : Temizoda O2 Eksikligi Izleyici (%19.5 Alarm), ASME DN50 0.5 barg OVC Patlama Diski & 1.563 Ohm Quench Bosaltma Bankasi (Exp150, 24.0 kg)
// material          : 316L
// temp_stage        : 300 K (OVC / duvar / raf)
// vacuum_grade      : Kriyo OVC / Atmosfer
// tolerance         : O2>=19.5%, 0.5 barg ASME
// computed_mass_kg  : 24.00000
// envelope_mm       : 1910.000 x 1217.500 x 1512.200
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 1910.0000;
bbox_y = 1217.5000;
bbox_z = 1512.2000;

// Part-specific parametric dimensions
dn_size = "DN50";
burst_barg = 0.5;
r_dump_ohm = 1.563;
o2_alarm_pct = 19.5;

// Interface / port parameters (mm)
port_ovc_dn50_rupture_inlet_od = 75.000;
port_ovc_dn50_rupture_inlet_bore = 50.000;

module part_S7_SAFETY_05() {
  union() {
    // ASME DN50 0.5 barg OVC rupture-disk nozzle
    rotate([90.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=75.000, h=40.000, center=true);
        cylinder(d=50.000, h=42.000, center=true);
      }
    }
    // Burst disk clamping collar
    translate([0.000, 34.000, 0.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=108.000, h=24.000, center=true);
    // 1.563 Ohm quench dump resistor bank
    translate([1530.000, 105.500, -580.800]) cube([250.000, 240.000, 238.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 204.500, 820.000]) rotate([0.000, 0.000, 0.000]) part_S7_SAFETY_05();

part_S7_SAFETY_05();
