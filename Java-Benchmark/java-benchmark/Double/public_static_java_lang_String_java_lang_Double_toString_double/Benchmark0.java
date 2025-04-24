

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = Double.toString(input_1_0);
        String output_2 = Double.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("1.8873761222661256E141") && output_2.equals("-2.945923609168024E132")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

