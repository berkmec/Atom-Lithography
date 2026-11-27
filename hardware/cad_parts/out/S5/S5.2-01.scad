// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.2-01)
// ============================================================================
// part_id           : S5.2-01
// parent_bom_id     : S5.2
// subsystem         : S5
// part_name         : UHV turbomolekuler pompa (HiPace 300 sinifi) + titresim korugu
// material          : Al 6061
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : <0.01 um titresim
// computed_mass_kg  : 14.99950
// envelope_mm       : 202.500 x 256.500 x 609.250
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 202.5000;
bbox_y = 256.5000;
bbox_z = 609.2500;

// Part-specific parametric dimensions
speed_N2_L_s = 260;
s_eff_N2_L_s = 206.3;
duct_id_mm = 152.4;
bellows_conv = 10;
tmp_od_mm = 136.0;

// Interface / port parameters (mm)
port_chamber_cf150_inlet_od = 202.500;
port_chamber_cf150_inlet_bore = 152.400;
port_chamber_cf150_inlet_pcd = 181.000;
port_chamber_cf150_inlet_bolts = 20;
port_vacion_top_tee_port_od = 152.000;
port_vacion_top_tee_port_bore = 101.600;
port_vacion_top_tee_port_pcd = 130.200;
port_vacion_top_tee_port_bolts = 16;
port_kf25_foreline_out_od = 40.000;
port_kf25_foreline_out_bore = 25.000;

module part_S5_2_01() {
  union() {
    // Chamber-side CF150 high-conductance bellows flange
    translate([0.000, 153.400, 0.000]) rotate([-90.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=202.500, h=22.200, center=true);
        cylinder(d=152.400, h=24.200, center=true);
        translate([0, 0, 9.850]) cylinder(d=171.300, h=1.750);
        for (i = [0 : 20 - 1])
          rotate([0, 0, i * 360 / 20])
            translate([90.500, 0, 0])
              cylinder(d=8.400, h=24.200, center=true);
      }
    }
    // 10-conv short CF150 vibration isolation bellows
    translate([0.000, 122.750, 0.000]) rotate([90.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=176.000, h=38.700, center=true);
        cylinder(d=151.000, h=40.700, center=true);
      }
    }
    // Top CF100 tee flange for S5.2-02 VacIon/TSP (Z=607.8 mm)
    translate([0.000, 0.000, 89.900]) {
      difference() {
        cylinder(d=152.000, h=19.800, center=true);
        cylinder(d=101.600, h=21.800, center=true);
        translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
        for (i = [0 : 16 - 1])
          rotate([0, 0, i * 360 / 16])
            translate([65.100, 0, 0])
              cylinder(d=8.400, h=21.800, center=true);
      }
    }
    // 300 L/s mag-lev turbomolecular pump body
    translate([0.000, 0.000, -194.200]) cylinder(d=136.000, h=187.500, center=true);
    // Mag-lev drive electronics module
    translate([76.000, 0.000, -228.000]) cube([32.000, 74.000, 96.000], center=true);
    // Pump station floor frame
    translate([0.000, 0.000, -398.250]) cube([140.000, 140.000, 219.500], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, -425.000, 508.000]) rotate([0.000, 0.000, 0.000]) part_S5_2_01();

part_S5_2_01();
