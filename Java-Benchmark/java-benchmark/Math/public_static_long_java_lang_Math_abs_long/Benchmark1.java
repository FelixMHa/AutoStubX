

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Math.abs(input_1_0);
        Long output_2 = Math.abs(input_2_0);

        
        // Compare output
        if (output_1 == 116L && output_2 == 34276408676813L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

