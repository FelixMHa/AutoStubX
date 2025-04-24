

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.intValue();
        Integer output_2 = input_2_0.intValue();

        
        // Compare output
        if (output_1 == 28 && output_2 == 1183) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

