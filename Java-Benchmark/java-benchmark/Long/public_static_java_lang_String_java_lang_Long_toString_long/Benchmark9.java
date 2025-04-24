

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toString(input_1_0);
        String output_2 = Long.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("-3288141") && output_2.equals("-391224")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

