

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_1_1 = Long.valueOf(args[1]);
        Long input_2_0 = Long.valueOf(args[2]);
        Long input_2_1 = Long.valueOf(args[3]);


        // Perform computation         
        Long output_1 = Math.max(input_1_0, input_1_1);
        Long output_2 = Math.max(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == 118361403L && output_2 == 22417175L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

