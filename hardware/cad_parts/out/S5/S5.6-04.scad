// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.6-04)
// ============================================================================
// part_id           : S5.6-04
// parent_bom_id     : S5.6
// subsystem         : S5
// part_name         : Yuk-kilidi S5.6 kompakt 80 L/s TMP + NEG yardimci UHV pompalama paketi (Exp139, 3.0 kg)
// material          : Al 6061
// temp_stage        : 300 K
// vacuum_grade      : UHV 1.5e-10 Torr
// tolerance         : <=1.5e-10 Torr
// computed_mass_kg  : 2.57626
// envelope_mm       : 133.000 x 113.500 x 213.200
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 133.0000;
bbox_y = 113.5000;
bbox_z = 213.2000;

// Part-specific parametric dimensions
tmp_speed_L_s = 80.0;
p_base_torr = 1.5e-10;
tmp_od_mm = 82.0;

// Interface / port parameters (mm)
port_mbe_cf63_inlet_od = 113.500;
port_mbe_cf63_inlet_bore = 63.500;
port_mbe_cf63_inlet_pcd = 92.100;
port_mbe_cf63_inlet_bolts = 8;
port_kf16_backing_out_bore = 16.000;

module part_S5_6_04() {
  union() {
    // Mating CF63 flange on S5.6-01 +X port
    translate([8.750, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        cylinder(d=63.500, h=19.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // CF63 MBE differential pumping tee
    translate([55.600, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=69.000, h=76.000, center=true);
        cylinder(d=63.000, h=78.000, center=true);
      }
    }
    // ZrVFe St172 NEG cartridge chamber
    translate([72.000, 0.000, 75.000]) {
      difference() {
        cylinder(d=76.000, h=56.000, center=true);
        cylinder(d=62.000, h=58.000, center=true);
      }
    }
    // 80 L/s compact HiPace-80 class TMP
    translate([72.000, 0.000, -72.500]) cylinder(d=82.000, h=51.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([514.500, 0.000, 710.000]) rotate([0.000, 0.000, 0.000]) part_S5_6_04();

part_S5_6_04();
